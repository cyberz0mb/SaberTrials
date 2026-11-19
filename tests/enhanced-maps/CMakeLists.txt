cmake_minimum_required(VERSION 3.15)
project(SaberTrialsBspCheck LANGUAGES CXX)

add_executable(st-bsp-check bsp_check.cpp)
target_compile_features(st-bsp-check PRIVATE cxx_std_17)
target_include_directories(st-bsp-check PRIVATE
    "${ST_ENGINE_SOURCE}/codemp"
    "${ST_ENGINE_SOURCE}/codemp/qcommon"
    "${ST_ENGINE_SOURCE}/shared"
    "../../development-source/enhanced-maps"
)
