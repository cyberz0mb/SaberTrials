cmake_minimum_required(VERSION 3.16)
project(WeaponDLCTests C)
enable_testing()
if(NOT ST_DLC_ENGINE)
  message(FATAL_ERROR "Set ST_DLC_ENGINE to a combined OpenJK tree")
endif()
add_executable(weapon_dlc_tests runtime.c
    "${ST_DLC_ENGINE}/codemp/qcommon/q_shared.c"
    "${ST_DLC_ENGINE}/shared/qcommon/q_string.c"
    "${ST_DLC_ENGINE}/codemp/game/bg_weapons.c")
target_include_directories(weapon_dlc_tests PRIVATE "${ST_DLC_ENGINE}/codemp" "${ST_DLC_ENGINE}/shared"
    ../../development-source/weapon-dlc)
if(MSVC)
    target_compile_options(weapon_dlc_tests PRIVATE /UNDEBUG)
    target_compile_definitions(weapon_dlc_tests PRIVATE _CRT_SECURE_NO_WARNINGS)
endif()
add_test(NAME weapon_dlc_runtime COMMAND weapon_dlc_tests)
