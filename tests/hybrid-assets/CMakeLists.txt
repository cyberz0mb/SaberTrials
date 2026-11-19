cmake_minimum_required(VERSION 3.15)
project(hybrid_assets_checks LANGUAGES CXX)
if(NOT ST_CANDIDATE)
  message(FATAL_ERROR "Set ST_CANDIDATE to the isolated generated candidate")
endif()
add_executable(hybrid_assets_checks main.cpp)
target_include_directories(hybrid_assets_checks PRIVATE "${ST_CANDIDATE}/game/codemp/game")
target_compile_features(hybrid_assets_checks PRIVATE cxx_std_11)
enable_testing()
add_test(NAME hybrid_assets_checks COMMAND hybrid_assets_checks)

# Exercise the engine's actual comparator, including its uppercase folding.
# A lowercase/Python sort gives the wrong answer for an underscore versus Z.
file(READ "${ST_CANDIDATE}/engine/codemp/qcommon/files.cpp" fs_source)
string(FIND "${fs_source}" "int FS_PathCmp( const char *s1, const char *s2 ) {" fs_start)
if(fs_start LESS 0)
  message(FATAL_ERROR "Engine FS_PathCmp entry point changed")
endif()
string(SUBSTRING "${fs_source}" ${fs_start} -1 fs_tail)
string(FIND "${fs_tail}" "\n}" fs_end)
if(fs_end LESS 0)
  message(FATAL_ERROR "Engine FS_PathCmp end not found")
endif()
math(EXPR fs_length "${fs_end}+2")
string(SUBSTRING "${fs_tail}" 0 ${fs_length} fs_comparator)
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/fs_pathcmp_under_test.h" "${fs_comparator}\n")
add_executable(hybrid_package_priority package_priority.cpp)
target_include_directories(hybrid_package_priority PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
target_compile_features(hybrid_package_priority PRIVATE cxx_std_11)
file(GLOB candidate_packages "${ST_CANDIDATE}/assets/*.pk3")
list(REMOVE_ITEM candidate_packages "${ST_CANDIDATE}/assets/zz_sabertrials_stances_v1.pk3")
list(LENGTH candidate_packages expanded_package_count)
if(NOT expanded_package_count EQUAL 1)
  message(FATAL_ERROR "Expected exactly one expanded animation package alongside the stance library")
endif()
list(GET candidate_packages 0 expanded_package)
get_filename_component(expanded_name "${expanded_package}" NAME)
add_test(NAME hybrid_package_priority COMMAND hybrid_package_priority
  "zz_sabertrials_stances_v1.pk3" "${expanded_name}")

find_package(Python3 REQUIRED COMPONENTS Interpreter)
if(NOT ST_UI_SOURCE)
  set(ST_UI_SOURCE "${ST_CANDIDATE}/frontend")
endif()
execute_process(COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/prepare_parser_test.py"
  "${ST_CANDIDATE}" "${CMAKE_CURRENT_BINARY_DIR}/parser-fixtures"
  --ui-source "${ST_UI_SOURCE}"
  RESULT_VARIABLE parser_prepare_result)
if(NOT parser_prepare_result EQUAL 0)
  message(FATAL_ERROR "Could not extract production animation parser/fixtures")
endif()
add_executable(hybrid_animation_parser parser.cpp)
target_include_directories(hybrid_animation_parser PRIVATE
  "${CMAKE_CURRENT_BINARY_DIR}/parser-fixtures"
  "${ST_CANDIDATE}/game/codemp/game" "${ST_CANDIDATE}/game/codemp/cgame")
target_compile_features(hybrid_animation_parser PRIVATE cxx_std_11)
target_compile_definitions(hybrid_animation_parser PRIVATE _CRT_SECURE_NO_WARNINGS)
add_test(NAME hybrid_animation_parser COMMAND hybrid_animation_parser
  "${CMAKE_CURRENT_BINARY_DIR}/parser-fixtures")

# Main-menu startup/model previews use a different implementation from BG.
add_executable(hybrid_ui_animation_parser parser.cpp)
target_include_directories(hybrid_ui_animation_parser PRIVATE
  "${CMAKE_CURRENT_BINARY_DIR}/parser-fixtures"
  "${ST_UI_SOURCE}/codemp/game" "${ST_UI_SOURCE}/codemp/cgame")
target_compile_features(hybrid_ui_animation_parser PRIVATE cxx_std_11)
target_compile_definitions(hybrid_ui_animation_parser PRIVATE _CRT_SECURE_NO_WARNINGS ST_TEST_UI)
add_test(NAME hybrid_ui_animation_parser COMMAND hybrid_ui_animation_parser
  "${CMAKE_CURRENT_BINARY_DIR}/parser-fixtures")
