from ctypes import c_float
from pymetal import PyMetal

metal = PyMetal()

code = """
#include <metal_stdlib>
using namespace metal;

kernel void add(
    device float  *out [[ buffer(1) ]],
    const device float2 *in [[ buffer(0) ]],
    uint id [[ thread_position_in_grid ]]
) {
    out[id] = in[id].x + in[id].y;
}
"""

metal.compile("add", code)
input_buffer = (c_float * 2)(*[1, 2])

device_input_buffer = metal.new_device_buffer_bytes(2, input_buffer)
device_output_buffer = metal.new_device_buffer_empty(1)
metal.run(
    bufs=[
        device_input_buffer,
        device_output_buffer,
    ],
    threadgroups=(1, 1, 1),
    threadPerThreadgroup=(1, 1, 1),
)
output = metal.copy_out(device_output_buffer)
print((c_float * 1).from_address(output)[:])
