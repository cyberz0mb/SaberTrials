cmake_minimum_required(VERSION 3.16)
project(selection_checks LANGUAGES CXX)
add_executable(selection_checks selection.cpp)
target_include_directories(selection_checks PRIVATE "${FRONTEND_SOURCE}/codemp/ui")
target_compile_features(selection_checks PRIVATE cxx_std_11)

find_package(Python3 COMPONENTS Interpreter REQUIRED)
set(cg_dir "${FRONTEND_SOURCE}/codemp/cgame")
add_custom_command(OUTPUT "${CMAKE_BINARY_DIR}/name-check.cpp"
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/generate_name_check.py" "${CMAKE_BINARY_DIR}/name-check.cpp" "${cg_dir}"
    DEPENDS generate_name_check.py "${cg_dir}/cg_players.c" "${cg_dir}/cg_draw.c"
    VERBATIM)
add_executable(name_checks "${CMAKE_BINARY_DIR}/name-check.cpp")
enable_testing()
add_test(NAME formats_and_presets COMMAND selection_checks)
add_test(NAME colored_and_private_names COMMAND name_checks)
