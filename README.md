# Pymetal: Lightweight python interface for Mac's Metal API

This library allows you to interface with the Metal API directly in
python, without the heavy dependency of py-objc bridge

**Note: experimental phase, not fully tested yet**

## Usage:
### 1. Import the module to see if your system is compatible

```python
from pymetal import PyMetal
metal = PyMetal()
```

If there's no error, things are initialized properly.

### 2. Compile some GPU code:

```python

metal.compile("add", """
kernel void add(
    device float  *out [[ buffer(1) ]],
    const device float2 *in [[ buffer(0) ]],
    uint id [[ thread_position_in_grid ]]
) {
    out[id] = in[id].x + in[id].y;
}
""")
```

### 3. Initilaize the input and output buffers on the device:

```python
input_buffer = (c_float * 2)(*[1, 2])
device_input_buffer = metal.new_device_buffer_bytes(2, input_buffer)
device_output_buffer = metal.new_device_buffer_empty(1)
```

### 4. Compute
```python
metal.run(
    bufs=[
        device_input_buffer,
        device_output_buffer,
    ],
    threadgroups=(1, 1, 1),
    threadPerThreadgroup=(1, 1, 1),
)
```

### 5. View the result
```python
output = metal.copy_out(device_output_buffer)
print((c_float * 1).from_address(output)[:]) # [3.0]
```