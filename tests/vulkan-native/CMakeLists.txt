cmake_minimum_required(VERSION 3.20)
project(st_vulkan_native LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 14)
add_executable(vulkan_contracts core.cpp)
target_include_directories(vulkan_contracts PRIVATE
  ../../dist/vulkan-01/engine/codemp/client
  ../../development-source/vulkan)
enable_testing()
add_test(NAME vulkan_contracts COMMAND vulkan_contracts)
