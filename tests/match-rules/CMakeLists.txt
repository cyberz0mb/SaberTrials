cmake_minimum_required(VERSION 3.16)
project(SaberTrialsMatchRulesChecks LANGUAGES CXX)
enable_testing()
# These are check executables: standard assertions must run in every build mode.
foreach(flag CMAKE_CXX_FLAGS CMAKE_CXX_FLAGS_RELEASE CMAKE_CXX_FLAGS_RELWITHDEBINFO CMAKE_CXX_FLAGS_MINSIZEREL)
  string(REPLACE "/DNDEBUG" "" ${flag} "${${flag}}")
  string(REPLACE "-DNDEBUG" "" ${flag} "${${flag}}")
endforeach()

get_filename_component(ST_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)
set(ST_MATCH_RULES "${ST_ROOT}/development-source/match-rules" CACHE PATH "Match Rules production header directory")

function(match_rules_target name source)
  add_executable(${name} "${source}")
  target_compile_features(${name} PRIVATE cxx_std_11)
  target_include_directories(${name} PRIVATE "${ST_MATCH_RULES}")
  if(MSVC)
    target_compile_options(${name} PRIVATE /W4 /permissive-)
  else()
    target_compile_options(${name} PRIVATE -Wall -Wextra -pedantic)
  endif()
endfunction()

match_rules_target(match_rules_core core.cpp)
foreach(group catalog roundtrip malformed validation)
  add_test(NAME match_rules_${group} COMMAND match_rules_core ${group})
endforeach()

if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/server_policy.cpp")
  match_rules_target(match_rules_server_policy server_policy.cpp)
  add_test(NAME match_rules_server_policy COMMAND match_rules_server_policy)
endif()

match_rules_target(match_rules_ui "${ST_MATCH_RULES}/ui_tests.cpp")
set(ST_MATCH_RULES_UI_HEADERS "${CMAKE_CURRENT_SOURCE_DIR}/../../dist/black-sabers-01/frontend/codemp/ui"
    CACHE PATH "OpenJK UI headers for the native UI check")
target_include_directories(match_rules_ui PRIVATE "${ST_MATCH_RULES_UI_HEADERS}")
add_test(NAME match_rules_ui_transactions COMMAND match_rules_ui)

match_rules_target(match_rules_server_adapter server_adapter.cpp)
add_test(NAME match_rules_server_adapter COMMAND match_rules_server_adapter)
