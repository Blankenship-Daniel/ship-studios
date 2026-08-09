cmake_minimum_required(VERSION 3.22)

project(ShipStudiosMcpPlugin VERSION 0.1.0 LANGUAGES C CXX)

# --- Build options ---------------------------------------------------------
# Universal (arm64 + x86_64) is what you want for anything you hand to another
# machine. It roughly doubles build time, so flip it off for fast local dev:
#   cmake -B build -D SHIPSTUDIOS_UNIVERSAL=OFF
option(SHIPSTUDIOS_UNIVERSAL "Build a macOS universal binary (arm64 + x86_64)" ON)

if(APPLE)
  # Must be set before any target is defined, and before JUCE is configured.
  if(SHIPSTUDIOS_UNIVERSAL)
    set(CMAKE_OSX_ARCHITECTURES "arm64;x86_64" CACHE STRING "" FORCE)
  endif()
  # 10.13 is JUCE 8's floor and covers every macOS that runs a current DAW.
  set(CMAKE_OSX_DEPLOYMENT_TARGET "10.13" CACHE STRING "" FORCE)
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# --- JUCE ------------------------------------------------------------------
# Fetched, not vendored: nothing to install by hand, and the version is pinned
# here so every machine builds the same framework. Kept in lockstep with
# ../vst/CMakeLists.txt -- two plugins on two JUCE versions is a debugging trap.
include(FetchContent)

set(JUCE_VERSION "8.0.15" CACHE STRING "JUCE version tag to build against")

FetchContent_Declare(JUCE
  GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
  GIT_TAG        ${JUCE_VERSION}
  GIT_SHALLOW    TRUE
  GIT_PROGRESS   TRUE)
FetchContent_MakeAvailable(JUCE)

# --- The plugin ------------------------------------------------------------
# FORMATS drives everything downstream:
#   AU         -> Logic Pro, GarageBand, LUNA   (Logic loads NOTHING else)
#   VST3       -> Ableton Live, Studio One, Cubase, Reaper, Bitwig, FL, LUNA
#   Standalone -> a .app for testing without opening a DAW
# AAX (Pro Tools) is deliberately absent: it needs Avid's SDK + PACE signing.
#
# PLUGIN_CODE and BUNDLE_ID are how a host finds this plugin in a saved
# session. They are distinct from Distance's (Sdt1 / com.shipstudios.distance)
# and must stay frozen from the first session that references them -- changing
# either after release orphans every project using the old codes.
juce_add_plugin(ShipStudiosMcp
  PRODUCT_NAME              "Ship Studios MCP"
  COMPANY_NAME              "Ship Studios"
  BUNDLE_ID                 "com.shipstudios.mcp"

  # Both codes are 4 characters. AU requires at least one uppercase letter in
  # the manufacturer code -- an all-lowercase code fails auval.
  PLUGIN_MANUFACTURER_CODE  Shst
  PLUGIN_CODE               Smc1

  FORMATS                   AU VST3 Standalone

  IS_SYNTH                  FALSE
  NEEDS_MIDI_INPUT          FALSE
  NEEDS_MIDI_OUTPUT         FALSE
  IS_MIDI_EFFECT            FALSE
  EDITOR_WANTS_KEYBOARD_FOCUS FALSE

  # Drops the built AU/VST3 straight into ~/Library/Audio/Plug-Ins/ so Logic
  # and Live see it on their next scan. Set to FALSE if you'd rather install
  # by hand.
  COPY_PLUGIN_AFTER_BUILD   TRUE

  VST3_CATEGORIES           Fx Tools
  AU_MAIN_TYPE              kAudioUnitType_Effect)

target_sources(ShipStudiosMcp PRIVATE
  Source/PluginProcessor.cpp
  Source/PluginEditor.cpp)

target_include_directories(ShipStudiosMcp PRIVATE Source)

target_compile_definitions(ShipStudiosMcp PUBLIC
  JUCE_WEB_BROWSER=0
  JUCE_USE_CURL=0
  JUCE_VST3_CAN_REPLACE_VST2=0
  JUCE_DISPLAY_SPLASH_SCREEN=0
  JUCE_REPORT_APP_USAGE=0)

target_link_libraries(ShipStudiosMcp
  PRIVATE
    juce::juce_audio_utils
    juce::juce_dsp
  PUBLIC
    juce::juce_recommended_config_flags
    juce::juce_recommended_lto_flags
    juce::juce_recommended_warning_flags)
