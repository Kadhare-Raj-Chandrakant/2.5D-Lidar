#include <pybind11/pybind11.h>
#include <pybind11/eigen.h>
#include <pybind11/stl.h>
#include <fastdem/fastdem.hpp>

namespace py = pybind11;

// Minimal surface matching SPEC.md; extend with Kalman/P2 + raycast options.
PYBIND11_MODULE(fastdem_pybind, m) {
    m.doc() = "FastDEM pybind11 surface for fovea_lidar";
    py::class_<fastdem::ElevationMap>(m, "ElevationMap")
        .def(py::init<>())
        .def("setGeometry", &fastdem::ElevationMap::setGeometry)
        .def("getHeight", &fastdem::ElevationMap::getHeight)
        .def("getUncertainty", &fastdem::ElevationMap::getUncertainty);
    py::class_<fastdem::FastDEM>(m, "FastDEM")
        .def(py::init<fastdem::ElevationMap&>())
        .def("setMappingMode", &fastdem::FastDEM::setMappingMode)
        .def("setEstimatorType", &fastdem::FastDEM::setEstimatorType)
        .def("integrate", static_cast<bool (fastdem::FastDEM::*)(
                  const fastdem::PointCloud&,
                  const Eigen::Isometry3d&,
                  const Eigen::Isometry3d&)>(&fastdem::FastDEM::integrate));
}
