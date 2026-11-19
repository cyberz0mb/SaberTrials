cmake_minimum_required(VERSION 3.16)
project(st_feint_integration C CXX)
enable_testing()
set(CMAKE_C_STANDARD 99)
set(CORE ../../development-source/combat-foundation)
add_executable(feint_adapter adapter.c ${CORE}/st_combat_core.c ${CORE}/st_combat_wire.c)
target_include_directories(feint_adapter PRIVATE ${CORE} ../../development-source/combat-integration)
add_test(NAME feint_adapter COMMAND feint_adapter)
if(ST_FEINT_ENGINE)
 configure_file("${ST_FEINT_ENGINE}/shared/qcommon/q_version.h.in" qcommon/q_version.h)
 add_executable(feint_protocol protocol.cpp
  "${ST_FEINT_ENGINE}/codemp/qcommon/msg.cpp"
  "${ST_FEINT_ENGINE}/codemp/qcommon/huffman.cpp"
  "${ST_FEINT_ENGINE}/codemp/qcommon/q_shared.c"
  "${ST_FEINT_ENGINE}/shared/qcommon/q_math.c"
  "${ST_FEINT_ENGINE}/shared/qcommon/q_string.c")
 target_include_directories(feint_protocol PRIVATE "${ST_FEINT_ENGINE}/codemp" "${ST_FEINT_ENGINE}/shared" "${CMAKE_CURRENT_BINARY_DIR}")
 set_source_files_properties("${ST_FEINT_ENGINE}/codemp/qcommon/q_shared.c"
  "${ST_FEINT_ENGINE}/shared/qcommon/q_math.c" "${ST_FEINT_ENGINE}/shared/qcommon/q_string.c" PROPERTIES LANGUAGE CXX)
 if(MSVC)
  target_compile_options(feint_protocol PRIVATE /Gy)
  target_link_options(feint_protocol PRIVATE /OPT:REF)
 endif()
 add_test(NAME feint_playerstate_protocol COMMAND feint_protocol)
endif()
if(ST_BASELINE_ENGINE)
 add_executable(feint_legacy_protocol protocol.cpp
  "${ST_BASELINE_ENGINE}/codemp/qcommon/msg.cpp"
  "${ST_BASELINE_ENGINE}/codemp/qcommon/huffman.cpp"
  "${ST_BASELINE_ENGINE}/codemp/qcommon/q_shared.c"
  "${ST_BASELINE_ENGINE}/shared/qcommon/q_math.c"
  "${ST_BASELINE_ENGINE}/shared/qcommon/q_string.c")
 target_compile_definitions(feint_legacy_protocol PRIVATE ST_PROTOCOL_BASELINE)
 target_include_directories(feint_legacy_protocol PRIVATE "${ST_BASELINE_ENGINE}/codemp" "${ST_BASELINE_ENGINE}/shared" "${CMAKE_CURRENT_BINARY_DIR}")
 set_source_files_properties("${ST_BASELINE_ENGINE}/codemp/qcommon/q_shared.c"
  "${ST_BASELINE_ENGINE}/shared/qcommon/q_math.c" "${ST_BASELINE_ENGINE}/shared/qcommon/q_string.c" PROPERTIES LANGUAGE CXX)
endif()
