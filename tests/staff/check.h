#pragma once
#include <stdexcept>
#include <iostream>
#define CHECK(x) do { if (!(x)) throw std::runtime_error("check failed: " #x); } while(0)
#define RUN_TEST(...) int main() { try { __VA_ARGS__; std::cout << "PASS\n"; return 0; } catch(const std::exception& e) { std::cerr << e.what() << "\n"; return 1; } }
