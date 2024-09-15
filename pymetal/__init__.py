import os
from ctypes import CDLL, c_void_p, c_char_p, Structure, c_ulong, Array, c_float, sizeof
from ctypes.macholib.dyld import dyld_find  # pyright: ignore
from typing import cast, Any, Optional, Tuple, List


class objc_id(c_void_p):
    pass


def load_library(path: str):
    return CDLL(
        cast(
            str,
            dyld_find(path),
        )
    )


libobjc = load_library(os.environ.get("LIBOBJC", "/usr/lib/libobjc.dylib"))
libobjc.objc_msgSend.restype = objc_id
libobjc.objc_getClass.restype = objc_id
libobjc.objc_getClass.argtypes = [c_char_p]
libobjc.sel_registerName.restype = objc_id
libobjc.sel_registerName.argtypes = [c_char_p]

metal = load_library(
    os.environ.get("METAL", "/Library/Frameworks/Metal.framework/Metal")
)
metal.MTLCreateSystemDefaultDevice.restype = objc_id

core_graphics = load_library(
    os.environ.get(
        "CORE_GRAPHICS",
        "/Library/Frameworks/CoreGraphics.framework/CoreGraphics",
    )
)


def send_message(ptr: objc_id, selector: str, *args: Any) -> objc_id:
    return libobjc.objc_msgSend(
        ptr,
        libobjc.sel_registerName(selector.encode()),
        *args,
    )


NSString: objc_id = libobjc.objc_getClass(b"NSString")


def to_ns_str(s: str) -> objc_id:
    return send_message(NSString, "stringWithUTF8String:", s.encode())


def int_tuple_to_struct(t: tuple[int, ...]):
    class Struct(Structure):
        pass

    Struct._fields_ = [(f"field{i}", c_ulong) for i in range(len(t))]
    return Struct(*t)


def compile(
    source: str,
    kernel_name: str,
    device: Optional[objc_id] = None,
    options: Optional[objc_id] = None,
) -> objc_id:
    _device: objc_id = device or metal.MTLCreateSystemDefaultDevice()
    _options = options or send_message(
        libobjc.objc_getClass(b"MTLCompileOptions"),
        "new",
    )
    library = send_message(
        _device,
        "newLibraryWithSource:options:error:",
        to_ns_str(source),
        _options,
        None,
    )
    kernelFunction = send_message(
        library,
        "newFunctionWithName:",
        to_ns_str(kernel_name),
    )
    return kernelFunction


class PyMetal:
    def __init__(self):
        self.device: objc_id = metal.MTLCreateSystemDefaultDevice()
        self.compileOptions: Optional[objc_id] = None
        self.library: Optional[objc_id] = None
        self.kernelFunction: Optional[objc_id] = None

        self.commandQueue = send_message(self.device, "newCommandQueue")
        self.commandBuffer = send_message(self.commandQueue, "commandBuffer")
        self.encoder = send_message(self.commandBuffer, "computeCommandEncoder")

    def compile(self, kernel_name: str, code: str):
        self.options = send_message(
            libobjc.objc_getClass(b"MTLCompileOptions"),
            "new",
        )
        self.library = send_message(
            self.device,
            "newLibraryWithSource:options:error:",
            to_ns_str(code),
            self.options,
            None,
        )
        self.kernelFunction = send_message(
            self.library,
            "newFunctionWithName:",
            to_ns_str(kernel_name),
        )
        self.computePipelineState = send_message(
            self.device,
            "newComputePipelineStateWithFunction:error:",
            self.kernelFunction,
            None,
        )
        send_message(
            self.encoder,
            "setComputePipelineState:",
            self.computePipelineState,
        )
        self.bufs: List[objc_id] = []

    def new_device_buffer_bytes(self, num_elements: int, buf: Array[c_float]):
        return send_message(
            self.device,
            "newBufferWithBytes:length:options:",
            buf,
            num_elements * sizeof(c_float),
            0,
        )

    def new_device_buffer_empty(self, num_elem: int):
        return send_message(
            self.device,
            "newBufferWithLength:options:",
            num_elem * sizeof(c_float),
            0,
        )

    def copy_out(self, buf: objc_id) -> int:
        """The integer value represent the address of the buffer"""
        ret = send_message(buf, "contents").value
        assert ret
        return ret

    def run(
        self,
        bufs: List[objc_id],
        threadgroups: Tuple[int, int, int],
        threadPerThreadgroup: Tuple[int, int, int],
    ):
        for i, buf in enumerate(bufs):
            send_message(self.encoder, "setBuffer:offset:atIndex:", buf, 0, i)
        send_message(
            self.encoder,
            "dispatchThreadgroups:threadsPerThreadgroup:",
            int_tuple_to_struct(threadgroups),
            int_tuple_to_struct(threadPerThreadgroup),
        )
        send_message(self.encoder, "endEncoding")

        send_message(self.commandBuffer, "commit")

        send_message(self.commandBuffer, "waitUntilCompleted")
