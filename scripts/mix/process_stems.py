"""Execute per-stem corrective + API-console-color plans on drum stems.

    python process_stems.py <plans.json> <src_dir> <out_dir> [duration_s=0]

plans.json = [{stem, clean, eq_bands, de_harsh, dynamic_eq, transient, excite, color_api, ...}, ...]
(the schema emitted by the drum-stem-diagnosis workflow). Each stem flows:
  src -> clean_loop(declick=FALSE) -> apply_eq(phase=zero) -> suppress_resonances -> apply_dynamic_eq
      -> shape_bands -> excite_loop  -> API Vision Channel Strip color  -> out
Only the stages present in the plan run. Mono inputs stay mono. Measures before/after + verifies.

Run with the stemmy-loops vst venv (pedalboard + the tools). duration_s>0 processes only the
first N seconds (for a fast audition); 0 = full length.
"""
import sys, json, tempfile, os
import numpy as np, soundfile as sf
from pedalboard import load_plugin, Pedalboard
from stemmy.loops_mcp.tools.clean_loop import clean_loop
from stemmy.loops_mcp.tools.apply_eq import apply_eq
from stemmy.loops_mcp.tools.suppress_resonances import suppress_resonances
from stemmy.loops_mcp.tools.apply_dynamic_eq import apply_dynamic_eq
from stemmy.loops_mcp.tools.shape_bands import shape_bands
from stemmy.loops_mcp.tools.excite_loop import excite_loop
from stemmy.loops_mcp.tools.measure_loudness import measure_loudness
from stemmy.loops_mcp.tools.measure_spectrum import measure_spectrum
from stemmy.loops_mcp.tools.apply_eq import EqBand
from stemmy.loops_mcp._dsp.multiband import BandShape
from stemmy.loops_mcp.tools.apply_dynamic_eq import DynEqBand

API = "/Library/Audio/Plug-Ins/VST3/uaudio_api_vision_channel_strip.vst3"
LF = [30,40,50,100,200,300,400]; LMF=[75,150,180,240,500,700,1000]
HMF=[800,1500,3000,5000,8000,10000,12500]; HF=[2500,5000,7000,10000,12500,15000,20000]
GAINS=[-12,-9,-6,-4,-2,0,2,4,6,9,12]
def snap(v, grid): return min(grid, key=lambda g: abs(g-v))

def _tmp(): return tempfile.mktemp(suffix=".wav")

def dsp_chain(src, plan):
    """Run the file->file corrective tools; return path to the corrected wav."""
    cur = src
    c = plan.get("clean")
    if c:
        o=_tmp(); clean_loop(cur, o, hpf_hz=float(c.get("hpf_hz",30)), declick=False,
            denoise=bool(c.get("denoise",False)), denoise_db=float(c.get("denoise_db",12))); cur=o
    eb = plan.get("eq_bands") or []
    if eb:
        bands=[EqBand(type=b["type"], freq_hz=float(b["freq_hz"]), gain_db=float(b["gain_db"]), q=float(b.get("q",1.0))) for b in eb]
        o=_tmp(); apply_eq(cur, o, bands=bands, phase="zero"); cur=o
    dh = plan.get("de_harsh")
    if dh:
        fb=None
        if dh.get("focus_lo_hz") and dh.get("focus_hi_hz"): fb=(float(dh["focus_lo_hz"]),float(dh["focus_hi_hz"]))
        o=_tmp(); suppress_resonances(cur, o, depth=float(dh.get("depth",0.5)),
            max_reduction_db=float(dh.get("max_reduction_db",6.0)), focus_band=fb); cur=o
    de = plan.get("dynamic_eq")
    if de:
        bands=[DynEqBand(freq_hz=float(b["freq_hz"]), q=float(b.get("q",1.0)),
            threshold_dbfs=float(b.get("threshold_dbfs",-24)), ratio=float(b.get("ratio",4)),
            range_db=float(b.get("range_db",6)), mode=b.get("mode","cut")) for b in de]
        o=_tmp(); apply_dynamic_eq(cur, o, bands=bands); cur=o
    tr = plan.get("transient")
    if tr and tr.get("bands"):
        bands=[BandShape(transient=float(b["transient"]), gain_db=float(b.get("gain_db",0))) for b in tr["bands"]]
        o=_tmp(); shape_bands(cur, o, crossovers_hz=[float(x) for x in tr["crossovers_hz"]], bands=bands); cur=o
    ex = plan.get("excite")
    if ex:
        o=_tmp(); excite_loop(cur, o, band=ex.get("band","air"), drive_db=float(ex.get("drive_db",10)),
            mix=float(ex.get("mix",0.25))); cur=o
    return cur

def color(src, plan, out, mono):
    ca = plan.get("color_api") or {}
    p = load_plugin(API); fails=[]
    params = {"input_select":"Line", "line_gain": float(ca.get("line_gain_db",0.0)),
              "eq_on": False, "eq_type":"550L", "sc_link": True}
    _hp = float(ca.get("hp_filter_hz", 30))
    if _hp >= 12: params["215_on"]=True; params["215_hp_filter"]=_hp   # 215 HP valid range is 12-596 Hz
    else: params["215_on"]=False                                       # cutoff below range -> bypass the console HPF
    comp = ca.get("comp") or {}
    if comp.get("on"):
        params.update({"225_on":True, "225_type":comp.get("type","New (FF)"),
            "225_attack":comp.get("attack","Medium"),
            "225_ratio": round(float(comp.get("ratio",3.0))*2)/2,
            "225_thresh": max(-18.0, min(13.0, float(comp.get("thresh",0.0)))),
            "225_knee":"Hard", "225_release": f"{float(comp.get('release_s',0.30)):.2f} s"})
    eq = ca.get("eq") or {}
    if eq:
        params["eq_on"]=True
        for band,grid,fk,gk in [("lf",LF,"lf_freq","lf_gain"),("lmf",LMF,"lmf_freq","lmf_gain"),
                                 ("hmf",HMF,"hmf_freq","hmf_gain"),("hf",HF,"hf_freq","hf_gain")]:
            if eq.get(f"{band}_freq") is not None or eq.get(f"{band}_gain") is not None:
                g = snap(float(eq.get(f"{band}_gain",0)), GAINS)
                f = snap(float(eq.get(f"{band}_freq", grid[len(grid)//2])), grid)
                params[f"550_{fk}"]=float(f); params[f"550_{gk}"]=float(g)
    audio,sr=sf.read(src,dtype="float32",always_2d=True); x=audio.T.copy()
    if x.shape[0]==1: x=np.repeat(x,2,0)
    for k,v in params.items():
        try: setattr(p,k,v)
        except Exception as e: fails.append(f"{k}={v!r}")
    y=Pedalboard([p])(x,sr)
    pk=float(np.max(np.abs(y))); y=y*((10**(float(ca.get('output_peak_dbfs',-1.0))/20))/pk) if pk>0 else y
    if mono: y=y[:1]   # collapse dual-mono back to mono
    sf.write(out, y.T, sr, subtype="PCM_24")
    return params, fails

def m(path):
    L=measure_loudness(path).model_dump(); S=measure_spectrum(path).model_dump()
    return dict(lufs=L["integrated_lufs"], peak=L["sample_peak_dbfs"], crest=L["crest_factor_db"],
               cen=S["spectral_centroid_hz"], tilt=S["spectral_tilt_db_per_octave"])

def main():
    plans=json.load(open(sys.argv[1])); src_dir=sys.argv[2]; out_dir=sys.argv[3]
    dur=float(sys.argv[4]) if len(sys.argv)>4 else 0.0
    os.makedirs(out_dir, exist_ok=True)
    print(f"{'stem':<16}{'LUFS b>a':>14}{'crest b>a':>13}{'centroid b>a':>16}{'tilt b>a':>14}  notes")
    for plan in plans:
        name=os.path.basename(plan["stem"]); src=os.path.join(src_dir,name)
        if not os.path.exists(src): src=plan["stem"]
        info=sf.info(src); mono=(info.channels==1)
        work=src
        if dur>0:
            a,sr=sf.read(src,dtype="float32",always_2d=True); work=_tmp(); sf.write(work,a[:int(dur*sr)],sr,subtype="PCM_24")
        before=m(work)
        corrected=dsp_chain(work, plan)
        out=os.path.join(out_dir,name)
        params,fails=color(corrected, plan, out, mono)
        after=m(out)
        note = ("" if not fails else "FAIL:"+",".join(fails))
        print(f"{name:<16}{before['lufs']:>6.1f}>{after['lufs']:<6.1f}{before['crest']:>6.1f}>{after['crest']:<5.1f}"
              f"{before['cen']:>7.0f}>{after['cen']:<7.0f}{before['tilt']:>6.2f}>{after['tilt']:<6.2f}  {note}")
    print(f"\nwrote processed stems -> {out_dir}")

if __name__=="__main__":
    raise SystemExit(main())
