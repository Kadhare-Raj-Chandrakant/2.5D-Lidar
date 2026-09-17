cmake_minimum_required(VERSION 3.16)
project(fastdem_pybind)

find_package(pybind11 REQUIRED)
find_package(Eigen3 REQUIRED)

# FastDEM core lives in ../../FastDEM/fastdem
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../../FastDEM/fastdem fastdem_core)

pybind11_add_module(fastdem_pybind fastdem_pybind.cpp)
target_link_libraries(fastdem_pybind PRIVATE fastdem Eigen3::Eigen)
