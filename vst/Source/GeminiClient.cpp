#include "GeminiClient.h"

namespace ShipStudios
{

namespace
{
    /** The model, overridable without a rebuild.

        The default is the STABLE "-latest" alias, not a pinned preview:
        preview names get retired out from under a shipped binary (the API
        answers 404 and the UI can only say "HTTP 404"). Pro-tier because the
        window question is real audio-event localisation, not just a 5-way
        enum; set GEMINI_MODEL to try a flash-tier model -- the classification
        half was 3/3 on flash-class capability in earlier measurement. */
    juce::String geminiModel()
    {
        if (auto env = juce::SystemStats::getEnvironmentVariable ("GEMINI_MODEL", {});
            env.isNotEmpty())
            return env;

        return "gemini-pro-latest";
    }

    constexpr const char* keyPropertyName = "gemini_api_key";

    /** Downsampling target for the upload. Gemini downmixes to ~16 kbps mono
        regardless, so sending 48 kHz stereo buys nothing but upload time --
        and audio is billed at a flat 32 tokens/second either way. 16 kHz keeps
        the payload small while leaving every cue a classifier needs. */
    constexpr double uploadSampleRate = 16000.0;

    juce::PropertiesFile::Options keyFileOptions()
    {
        juce::PropertiesFile::Options o;
        o.applicationName = "Ship Studios";
        o.filenameSuffix = "settings";
        o.folderName = "Ship Studios";
        o.osxLibrarySubFolder = "Application Support";
        return o;
    }
}

juce::String GeminiClient::findApiKey (KeySource& sourceOut)
{
    // The environment first: it is the only source the pedalboard verification
    // harness has. It is ALSO unreliable in a DAW -- a plugin inherits the
    // host's environment, and Logic launched from Finder has no shell
    // variables at all -- which is why the file exists as a fallback.
    if (auto env = juce::SystemStats::getEnvironmentVariable ("GEMINI_API_KEY", {});
        env.isNotEmpty())
    {
        sourceOut = KeySource::environment;
        return env;
    }

    juce::PropertiesFile props (keyFileOptions());

    if (auto stored = props.getValue (keyPropertyName); stored.isNotEmpty())
    {
        sourceOut = KeySource::propertiesFile;
        return stored;
    }

    sourceOut = KeySource::none;
    return {};
}

void GeminiClient::storeApiKey (const juce::String& key)
{
    // PLAINTEXT, on purpose and stated plainly rather than implied: this writes
    // the key readable to anything running as the user. There is no keychain
    // integration. Prefer the environment variable if that matters to you.
    juce::PropertiesFile props (keyFileOptions());
    props.setValue (keyPropertyName, key);
    props.saveIfNeeded();
}

bool GeminiClient::hasApiKey()
{
    KeySource s {};
    return findApiKey (s).isNotEmpty();
}

Material GeminiClient::materialFromString (const juce::String& s) noexcept
{
    const auto t = s.trim().toLowerCase();

    if (t == "kick")      return Material::kick;
    if (t == "snare")     return Material::snare;
    if (t == "overheads") return Material::overheads;
    if (t == "drum_kit")  return Material::drumKit;
    if (t == "bass")      return Material::bass;
    if (t == "vocal")     return Material::vocal;
    if (t == "full_mix")  return Material::fullMix;
    if (t == "other")     return Material::other;

    // "drums" is not in the schema any more, but a model that ignores its own
    // enum -- which this repo has seen before -- should degrade to the whole-kit
    // strategy rather than to unknown.
    if (t == "drums")     return Material::drumKit;

    return Material::unknown;
}

juce::MemoryBlock GeminiClient::encodeWav (const float* samples, int numSamples, double sampleRate)
{
    // Naive decimation to ~16 kHz. Aliasing is irrelevant here: nothing
    // measures this buffer, it only has to remain recognisable to a classifier,
    // and the API's own codec is far more destructive than the fold-back.
    const auto step = juce::jmax (1, (int) std::round (sampleRate / uploadSampleRate));
    const auto outRate = sampleRate / (double) step;
    const auto outSamples = numSamples / step;

    juce::AudioBuffer<float> mono (1, juce::jmax (1, outSamples));
    auto* dst = mono.getWritePointer (0);

    for (int i = 0; i < outSamples; ++i)
        dst[i] = samples[i * step];

    juce::MemoryBlock block;
    juce::WavAudioFormat wav;

    if (auto* out = new juce::MemoryOutputStream (block, false))
    {
        std::unique_ptr<juce::AudioFormatWriter> writer (
            wav.createWriterFor (out, outRate, 1, 16, {}, 0));

        if (writer == nullptr)
        {
            delete out;
            return {};
        }

        writer->writeFromAudioSampleBuffer (mono, 0, outSamples);
    }

    return block;
}

juce::String GeminiClient::buildRequestJson (const juce::String& base64Wav)
{
    // response_schema pins the reply to the ONE field we act on. `note` is
    // free text for the UI; nothing parses it.
    //
    // No ambience field: it measured inverted on real material (a room mic came
    // back "moderate", the overheads "roomy"), so it is derived from crest.
    juce::DynamicObject::Ptr schemaProps (new juce::DynamicObject());
    {
        juce::DynamicObject::Ptr material (new juce::DynamicObject());
        material->setProperty ("type", "string");
        material->setProperty ("enum", juce::Array<juce::var> {
            "kick", "snare", "overheads", "drum_kit",
            "bass", "vocal", "full_mix", "other" });

        juce::DynamicObject::Ptr confidence (new juce::DynamicObject());
        confidence->setProperty ("type", "number");

        juce::DynamicObject::Ptr note (new juce::DynamicObject());
        note->setProperty ("type", "string");

        juce::DynamicObject::Ptr startS (new juce::DynamicObject());
        startS->setProperty ("type", "number");

        juce::DynamicObject::Ptr endS (new juce::DynamicObject());
        endS->setProperty ("type", "number");

        schemaProps->setProperty ("material", material.get());
        schemaProps->setProperty ("confidence", confidence.get());
        schemaProps->setProperty ("start_s", startS.get());
        schemaProps->setProperty ("end_s", endS.get());
        schemaProps->setProperty ("note", note.get());
    }

    juce::DynamicObject::Ptr schema (new juce::DynamicObject());
    schema->setProperty ("type", "object");
    schema->setProperty ("properties", schemaProps.get());
    schema->setProperty ("required", juce::Array<juce::var> {
        "material", "confidence", "start_s", "end_s" });

    juce::DynamicObject::Ptr genConfig (new juce::DynamicObject());
    genConfig->setProperty ("response_mime_type", "application/json");
    genConfig->setProperty ("response_schema", schema.get());
    genConfig->setProperty ("temperature", 0.0);

    juce::DynamicObject::Ptr inlineData (new juce::DynamicObject());
    inlineData->setProperty ("mime_type", "audio/wav");
    inlineData->setProperty ("data", base64Wav);

    juce::DynamicObject::Ptr audioPart (new juce::DynamicObject());
    audioPart->setProperty ("inline_data", inlineData.get());

    juce::DynamicObject::Ptr textPart (new juce::DynamicObject());
    textPart->setProperty ("text",
        "Two questions about this audio, and nothing else.\n\n"
        "1. material: what instrument or programme is this? Use \"kick\", "
        "\"snare\" or \"overheads\" for a single close or overhead drum mic, "
        "\"drum_kit\" for a whole kit or drum bus, \"full_mix\" for a finished "
        "mix. If you cannot tell, answer \"other\" with a low confidence.\n\n"
        "2. start_s / end_s: the seconds between which this recording is "
        "playing continuous, representative programme material. EXCLUDE silence, "
        "count-ins, talking, applause, fades and any lead-in before the "
        "performance starts. Give at least 3 seconds. If the whole clip is "
        "representative, give the whole clip.\n\n"
        "Do NOT comment on tone, brightness, level, room or distance, and do "
        "not suggest any processing.");

    juce::DynamicObject::Ptr content (new juce::DynamicObject());
    content->setProperty ("role", "user");
    content->setProperty ("parts", juce::Array<juce::var> { textPart.get(), audioPart.get() });

    juce::DynamicObject::Ptr root (new juce::DynamicObject());
    root->setProperty ("contents", juce::Array<juce::var> { content.get() });
    root->setProperty ("generationConfig", genConfig.get());

    return juce::JSON::toString (juce::var (root.get()), true);
}

//==============================================================================
juce::String GeminiClient::buildAssistJson (const juce::String& base64Wav, const Meters& m)
{
    juce::DynamicObject::Ptr props (new juce::DynamicObject());
    {
        const auto number = [] { juce::DynamicObject::Ptr o (new juce::DynamicObject());
                                 o->setProperty ("type", "number"); return o; };
        const auto boolean = [] { juce::DynamicObject::Ptr o (new juce::DynamicObject());
                                  o->setProperty ("type", "boolean"); return o; };
        const auto string = [] { juce::DynamicObject::Ptr o (new juce::DynamicObject());
                                 o->setProperty ("type", "string"); return o; };

        props->setProperty ("distance", number().get());
        props->setProperty ("extreme", boolean().get());
        props->setProperty ("hard_clip", boolean().get());
        props->setProperty ("ceiling_db", number().get());
        props->setProperty ("output_db", number().get());
        props->setProperty ("reasoning", string().get());
    }

    juce::DynamicObject::Ptr schema (new juce::DynamicObject());
    schema->setProperty ("type", "object");
    schema->setProperty ("properties", props.get());
    schema->setProperty ("required", juce::Array<juce::var> {
        "distance", "extreme", "hard_clip", "ceiling_db", "output_db", "reasoning" });

    juce::DynamicObject::Ptr genConfig (new juce::DynamicObject());
    genConfig->setProperty ("response_mime_type", "application/json");
    genConfig->setProperty ("response_schema", schema.get());
    genConfig->setProperty ("temperature", 0.0);

    juce::DynamicObject::Ptr inlineData (new juce::DynamicObject());
    inlineData->setProperty ("mime_type", "audio/wav");
    inlineData->setProperty ("data", base64Wav);

    juce::DynamicObject::Ptr audioPart (new juce::DynamicObject());
    audioPart->setProperty ("inline_data", inlineData.get());

    // GROUNDING. The audio it receives is a ~16 kbps mono downmix that destroys
    // level and skews the tonal balance by several dB/octave -- so the measured
    // numbers go in as facts to reason FROM, with the codec's failure mode
    // named outright so the model does not argue with them.
    const auto meterText =
        juce::String ("MEASURED (authoritative -- these come from the full-resolution "
                      "audio, the clip you are hearing is a low-bitrate mono downmix "
                      "that under-reads highs and over-reads lows; do not contradict "
                      "these numbers):\n")
        + "  peak " + juce::String (m.peakDb, 1) + " dBFS\n"
        + "  crest " + juce::String (m.crestDb, 1) + " dB\n"
        + "  spectral tilt " + juce::String (m.tiltDbPerOctave, 2) + " dB/octave\n"
        + "  centroid " + juce::String ((int) m.centroidHz) + " Hz\n"
        + "  balance (dB vs broadband mean): sub " + juce::String (m.bandDb[0], 1)
        + ", low " + juce::String (m.bandDb[1], 1)
        + ", mid " + juce::String (m.bandDb[2], 1)
        + ", high-mid " + juce::String (m.bandDb[3], 1)
        + ", air " + juce::String (m.bandDb[4], 1) + "\n";

    // Split so the meter block can sit between two runs of adjacent literals --
    // a juce::String() wrapper cannot be concatenated to a literal directly.
    const char* const brief =
        "You are setting a DISTANCE effect on this audio. One fader moves the "
        "source from far (-100) to close (+100); it applies a proximity/room/"
        "presence/air EQ, compression, transient shaping and a level law of "
        "6 dB per doubling of distance, all together.\n\n";

    const char* const askFor =
        "\nChoose:\n"
        "- distance: -100..+100. 0 is untouched. Negative pushes the source back "
        "and softens transients; positive brings it forward, tightens and "
        "brightens it. A crest above ~18 dB means transients are already intact "
        "and open; below ~10 dB the source is already dense or roomy.\n"
        "- extreme: true only if the material clearly wants MORE than the normal "
        "range can give.\n"
        "- hard_clip: false (soft, musical) for most material; true only for "
        "aggressive, already-distorted or deliberately harsh sources.\n"
        "- ceiling_db: -12..0 dBFS output ceiling. -0.3 unless the material "
        "needs more headroom.\n"
        "- output_db: -12..+12 makeup. Use 0 unless you have a reason.\n"
        "- reasoning: one short sentence, plain language, no numbers repeated.\n\n"
        "Be conservative. A setting near 0 is the right answer for material that "
        "does not need moving.";

    juce::DynamicObject::Ptr textPart (new juce::DynamicObject());
    textPart->setProperty ("text", juce::String (brief) + meterText + askFor);

    juce::DynamicObject::Ptr content (new juce::DynamicObject());
    content->setProperty ("role", "user");
    content->setProperty ("parts", juce::Array<juce::var> { textPart.get(), audioPart.get() });

    juce::DynamicObject::Ptr root (new juce::DynamicObject());
    root->setProperty ("contents", juce::Array<juce::var> { content.get() });
    root->setProperty ("generationConfig", genConfig.get());

    return juce::JSON::toString (juce::var (root.get()), true);
}

GeminiClient::Settings GeminiClient::suggestSettings (const float* samples,
                                                      int numSamples,
                                                      double sampleRate,
                                                      const Meters& meters,
                                                      NetworkCancel* cancel,
                                                      int timeoutMs)
{
    Settings out;

    KeySource source {};
    const auto key = findApiKey (source);

    if (key.isEmpty())
    {
        out.reasoning = "no API key";
        return out;
    }

    const auto wav = encodeWav (samples, numSamples, sampleRate);

    if (wav.getSize() == 0)
    {
        out.reasoning = "WAV encode failed";
        return out;
    }

    const auto body = buildAssistJson (juce::Base64::toBase64 (wav.getData(), wav.getSize()),
                                       meters);

    const juce::URL url (juce::String ("https://generativelanguage.googleapis.com/v1beta/models/")
                         + geminiModel() + ":generateContent");

    // Same cancellable transport as classify(), for the same reason: this
    // blocks on the worker thread, and teardown must be able to unblock it
    // rather than let stopThread degrade to a kill.
    juce::WebInputStream stream (url.withPOSTData (body), true);
    stream.withExtraHeaders (juce::String ("Content-Type: application/json\r\n")
                             + "x-goog-api-key: " + key)
          .withConnectionTimeout (timeoutMs);

    struct ScopedAttach
    {
        NetworkCancel* token;
        ~ScopedAttach() { if (token != nullptr) token->detach(); }
    } scopedAttach { cancel };

    if (cancel != nullptr)
        cancel->attach (&stream);

    if (! stream.connect (nullptr))
    {
        out.reasoning = (cancel != nullptr && cancel->isCancelled())
                            ? "cancelled" : "no network (host sandbox?)";
        return out;
    }

    const auto status = stream.getStatusCode();

    juce::MemoryOutputStream received;

    for (;;)
    {
        if (cancel != nullptr && cancel->isCancelled())
        {
            out.reasoning = "cancelled";
            return out;
        }

        char chunk[8192];
        const auto n = stream.read (chunk, (int) sizeof (chunk));

        if (n <= 0)
            break;

        received.write (chunk, (size_t) n);
    }

    const auto reply = received.toString();

    if (status < 200 || status >= 300)
    {
        out.reasoning = "HTTP " + juce::String (status);
        return out;
    }

    const auto parsed = juce::JSON::parse (reply);
    const auto* candidates = parsed.getProperty ("candidates", {}).getArray();

    if (candidates == nullptr || candidates->isEmpty())
    {
        out.reasoning = "no candidates";
        return out;
    }

    const auto* parts = candidates->getFirst()
                            .getProperty ("content", {})
                            .getProperty ("parts", {})
                            .getArray();

    if (parts == nullptr || parts->isEmpty())
    {
        out.reasoning = "empty reply";
        return out;
    }

    const auto inner = juce::JSON::parse (parts->getFirst().getProperty ("text", {}).toString());

    if (! inner.isObject())
    {
        out.reasoning = "unparseable reply";
        return out;
    }

    // CLAMPED, every one. Not defensive habit: this repo's own Python re-clamps
    // the same model's output (`_critique.py:141`) because it has been observed
    // returning values outside the bounds of the schema it was given. A NaN or
    // a +400 would otherwise walk straight into a parameter.
    const auto clamped = [] (const juce::var& v, float lo, float hi, float fallback)
    {
        const auto raw = (float) (double) v;
        return std::isfinite (raw) ? juce::jlimit (lo, hi, raw) : fallback;
    };

    out.distance  = clamped (inner.getProperty ("distance",   0.0), -100.0f, 100.0f,  0.0f);
    out.ceilingDb = clamped (inner.getProperty ("ceiling_db", -0.3), -12.0f,   0.0f, -0.3f);
    out.outputDb  = clamped (inner.getProperty ("output_db",  0.0),  -12.0f,  12.0f,  0.0f);
    out.extreme   = (bool) inner.getProperty ("extreme", false);
    out.hardClip  = (bool) inner.getProperty ("hard_clip", false);
    out.reasoning = inner.getProperty ("reasoning", {}).toString();
    out.ok = true;

    return out;
}

GeminiClient::Result GeminiClient::classify (const float* samples,
                                             int numSamples,
                                             double sampleRate,
                                             NetworkCancel* cancel,
                                             int timeoutMs)
{
    Result r;

    KeySource source {};
    const auto key = findApiKey (source);

    if (key.isEmpty())
    {
        r.note = "no API key";
        return r;
    }

    const auto wav = encodeWav (samples, numSamples, sampleRate);

    if (wav.getSize() == 0)
    {
        r.note = "WAV encode failed";
        return r;
    }

    const auto body = buildRequestJson (juce::Base64::toBase64 (wav.getData(), wav.getSize()));

    const juce::URL url (juce::String ("https://generativelanguage.googleapis.com/v1beta/models/")
                         + geminiModel() + ":generateContent");

    // WebInputStream rather than URL::createInputStream: it is the one JUCE
    // network primitive with a thread-safe cancel(), which is what lets the
    // processor's teardown unblock this call instead of force-killing the
    // worker after stopThread's timeout.
    juce::WebInputStream stream (url.withPOSTData (body), true);
    stream.withExtraHeaders (juce::String ("Content-Type: application/json\r\n")
                             + "x-goog-api-key: " + key)
          .withConnectionTimeout (timeoutMs);

    struct ScopedAttach
    {
        NetworkCancel* token;
        ~ScopedAttach() { if (token != nullptr) token->detach(); }
    } scopedAttach { cancel };

    if (cancel != nullptr)
        cancel->attach (&stream);

    if (! stream.connect (nullptr))
    {
        if (cancel != nullptr && cancel->isCancelled())
        {
            r.note = "cancelled";
            return r;
        }

        // The specific unknown flagged in the plan: a sandboxed AU host may
        // simply refuse outbound network. Say so rather than reporting a
        // generic failure the user cannot act on.
        r.note = "no network (host sandbox?)";
        return r;
    }

    const auto status = stream.getStatusCode();

    // Chunked rather than readEntireStreamAsString, with a cancel check per
    // chunk: a cancel() unblocks the CURRENT read, and this makes sure no
    // further read starts after it.
    juce::MemoryOutputStream received;

    for (;;)
    {
        if (cancel != nullptr && cancel->isCancelled())
        {
            r.note = "cancelled";
            return r;
        }

        char chunk[8192];
        const auto n = stream.read (chunk, (int) sizeof (chunk));

        if (n <= 0)
            break;

        received.write (chunk, (size_t) n);
    }

    const auto reply = received.toString();

    if (status < 200 || status >= 300)
    {
        r.note = "HTTP " + juce::String (status);
        return r;
    }

    const auto parsed = juce::JSON::parse (reply);
    const auto* candidates = parsed.getProperty ("candidates", {}).getArray();

    if (candidates == nullptr || candidates->isEmpty())
    {
        r.note = "no candidates";
        return r;
    }

    const auto* parts = candidates->getFirst()
                            .getProperty ("content", {})
                            .getProperty ("parts", {})
                            .getArray();

    if (parts == nullptr || parts->isEmpty())
    {
        r.note = "empty reply";
        return r;
    }

    // response_mime_type=application/json means the part's text IS the object.
    const auto inner = juce::JSON::parse (parts->getFirst().getProperty ("text", {}).toString());

    if (! inner.isObject())
    {
        r.note = "unparseable reply";
        return r;
    }

    r.material = materialFromString (inner.getProperty ("material", {}).toString());
    r.confidence = (float) (double) inner.getProperty ("confidence", 0.0);
    r.note = inner.getProperty ("note", {}).toString();

    // Validated here, not trusted: a window is only accepted if it is ordered,
    // inside the clip, and long enough to measure. The caller's DSP pick stands
    // otherwise -- an out-of-range answer must not become a silent no-op window.
    const auto startS = (float) (double) inner.getProperty ("start_s", -1.0);
    const auto endS   = (float) (double) inner.getProperty ("end_s", -1.0);
    const auto clipS  = (float) (numSamples / juce::jmax (1.0, sampleRate));

    if (startS >= 0.0f && endS > startS + 2.99f && startS < clipS)
    {
        r.hasWindow = true;
        r.windowStartS = startS;
        r.windowEndS = juce::jmin (endS, clipS);
    }

    // A low-confidence answer is worse than none: it would shift the search
    // windows on a guess, and the DSP result it displaces was measured.
    if (r.confidence < 0.5f)
    {
        r.material = Material::unknown;
        r.note = "low confidence (" + juce::String (r.confidence, 2) + ")";
        return r;
    }

    r.ok = r.material != Material::unknown;

    if (! r.ok && r.note.isEmpty())
        r.note = "unclassified";

    return r;
}

} // namespace ShipStudios
