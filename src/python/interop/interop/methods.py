# Copyright 2015, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Implementations of interoperability test methods."""

import threading

from grpc.early_adopter import utilities

from interop import empty_pb2
from interop import messages_pb2

_TIMEOUT = 7


def _empty_call(request, unused_context):
  return empty_pb2.Empty()

_CLIENT_EMPTY_CALL = utilities.unary_unary_invocation_description(
    empty_pb2.Empty.SerializeToString, empty_pb2.Empty.FromString)
_SERVER_EMPTY_CALL = utilities.unary_unary_service_description(
    _empty_call, empty_pb2.Empty.FromString,
    empty_pb2.Empty.SerializeToString)


def _unary_call(request, unused_context):
  return messages_pb2.SimpleResponse(
      payload=messages_pb2.Payload(
          type=messages_pb2.COMPRESSABLE,
          body=b'\x00' * request.response_size))

_CLIENT_UNARY_CALL = utilities.unary_unary_invocation_description(
    messages_pb2.SimpleRequest.SerializeToString,
    messages_pb2.SimpleResponse.FromString)
_SERVER_UNARY_CALL = utilities.unary_unary_service_description(
    _unary_call, messages_pb2.SimpleRequest.FromString,
    messages_pb2.SimpleResponse.SerializeToString)


def _streaming_output_call(request, unused_context):
  for response_parameters in request.response_parameters:
    yield messages_pb2.StreamingOutputCallResponse(
        payload=messages_pb2.Payload(
            type=request.response_type,
            body=b'\x00' * response_parameters.size))

_CLIENT_STREAMING_OUTPUT_CALL = utilities.unary_stream_invocation_description(
    messages_pb2.StreamingOutputCallRequest.SerializeToString,
    messages_pb2.StreamingOutputCallResponse.FromString)
_SERVER_STREAMING_OUTPUT_CALL = utilities.unary_stream_service_description(
    _streaming_output_call,
    messages_pb2.StreamingOutputCallRequest.FromString,
    messages_pb2.StreamingOutputCallResponse.SerializeToString)


def _streaming_input_call(request_iterator, unused_context):
  aggregate_size = 0
  for request in request_iterator:
    if request.payload and request.payload.body:
      aggregate_size += len(request.payload.body)
  return messages_pb2.StreamingInputCallResponse(
      aggregated_payload_size=aggregate_size)

_CLIENT_STREAMING_INPUT_CALL = utilities.stream_unary_invocation_description(
    messages_pb2.StreamingInputCallRequest.SerializeToString,
    messages_pb2.StreamingInputCallResponse.FromString)
_SERVER_STREAMING_INPUT_CALL = utilities.stream_unary_service_description(
    _streaming_input_call,
    messages_pb2.StreamingInputCallRequest.FromString,
    messages_pb2.StreamingInputCallResponse.SerializeToString)


def _full_duplex_call(request_iterator, unused_context):
  for request in request_iterator:
    yield messages_pb2.StreamingOutputCallResponse(
        payload=messages_pb2.Payload(
            type=request.payload.type,
            body=b'\x00' * request.response_parameters[0].size))

_CLIENT_FULL_DUPLEX_CALL = utilities.stream_stream_invocation_description(
    messages_pb2.StreamingOutputCallRequest.SerializeToString,
    messages_pb2.StreamingOutputCallResponse.FromString)
_SERVER_FULL_DUPLEX_CALL = utilities.stream_stream_service_description(
    _full_duplex_call,
    messages_pb2.StreamingOutputCallRequest.FromString,
    messages_pb2.StreamingOutputCallResponse.SerializeToString)

# NOTE(nathaniel): Apparently this is the same as the full-duplex call?
_CLIENT_HALF_DUPLEX_CALL = utilities.stream_stream_invocation_description(
    messages_pb2.StreamingOutputCallRequest.SerializeToString,
    messages_pb2.StreamingOutputCallResponse.FromString)
_SERVER_HALF_DUPLEX_CALL = utilities.stream_stream_service_description(
    _full_duplex_call,
    messages_pb2.StreamingOutputCallRequest.FromString,
    messages_pb2.StreamingOutputCallResponse.SerializeToString)


_SERVICE_NAME = '/grpc.testing.TestService'

EMPTY_CALL_METHOD_NAME = _SERVICE_NAME + '/EmptyCall'
UNARY_CALL_METHOD_NAME = _SERVICE_NAME + '/UnaryCall'
STREAMING_OUTPUT_CALL_METHOD_NAME = _SERVICE_NAME + '/StreamingOutputCall'
STREAMING_INPUT_CALL_METHOD_NAME = _SERVICE_NAME + '/StreamingInputCall'
FULL_DUPLEX_CALL_METHOD_NAME = _SERVICE_NAME + '/FullDuplexCall'
HALF_DUPLEX_CALL_METHOD_NAME = _SERVICE_NAME + '/HalfDuplexCall'

CLIENT_METHODS = {
    EMPTY_CALL_METHOD_NAME: _CLIENT_EMPTY_CALL,
    UNARY_CALL_METHOD_NAME: _CLIENT_UNARY_CALL,
    STREAMING_OUTPUT_CALL_METHOD_NAME: _CLIENT_STREAMING_OUTPUT_CALL,
    STREAMING_INPUT_CALL_METHOD_NAME: _CLIENT_STREAMING_INPUT_CALL,
    FULL_DUPLEX_CALL_METHOD_NAME: _CLIENT_FULL_DUPLEX_CALL,
    HALF_DUPLEX_CALL_METHOD_NAME: _CLIENT_HALF_DUPLEX_CALL,
}

SERVER_METHODS = {
    EMPTY_CALL_METHOD_NAME: _SERVER_EMPTY_CALL,
    UNARY_CALL_METHOD_NAME: _SERVER_UNARY_CALL,
    STREAMING_OUTPUT_CALL_METHOD_NAME: _SERVER_STREAMING_OUTPUT_CALL,
    STREAMING_INPUT_CALL_METHOD_NAME: _SERVER_STREAMING_INPUT_CALL,
    FULL_DUPLEX_CALL_METHOD_NAME: _SERVER_FULL_DUPLEX_CALL,
    HALF_DUPLEX_CALL_METHOD_NAME: _SERVER_HALF_DUPLEX_CALL,
}


def _empty_unary(stub):
  with stub:
    response = stub.EmptyCall(empty_pb2.Empty(), _TIMEOUT)
    if not isinstance(response, empty_pb2.Empty):
      raise TypeError(
          'response is of type "%s", not empty_pb2.Empty!', type(response))


def _large_unary(stub):
  with stub:
    request = messages_pb2.SimpleRequest(
        response_type=messages_pb2.COMPRESSABLE, response_size=314159,
        payload=messages_pb2.Payload(body=b'\x00' * 271828))
    response_future = stub.UnaryCall.async(request, _TIMEOUT)
    response = response_future.result()
    if response.payload.type is not messages_pb2.COMPRESSABLE:
      raise ValueError(
          'response payload type is "%s"!' % type(response.payload.type))
    if len(response.payload.body) != 314159:
      raise ValueError(
          'response body of incorrect size %d!' % len(response.payload.body))


def _client_streaming(stub):
  with stub:
    payload_body_sizes = (27182, 8, 1828, 45904)
    payloads = (
        messages_pb2.Payload(body=b'\x00' * size)
        for size in payload_body_sizes)
    requests = (
        messages_pb2.StreamingInputCallRequest(payload=payload)
        for payload in payloads)
    response = stub.StreamingInputCall(requests, _TIMEOUT)
    if response.aggregated_payload_size != 74922:
      raise ValueError(
          'incorrect size %d!' % response.aggregated_payload_size)


def _server_streaming(stub):
  sizes = (31415, 9, 2653, 58979)

  with stub:
    request = messages_pb2.StreamingOutputCallRequest(
        response_type=messages_pb2.COMPRESSABLE,
        response_parameters=(
            messages_pb2.ResponseParameters(size=sizes[0]),
            messages_pb2.ResponseParameters(size=sizes[1]),
            messages_pb2.ResponseParameters(size=sizes[2]),
            messages_pb2.ResponseParameters(size=sizes[3]),
        ))
    response_iterator = stub.StreamingOutputCall(request, _TIMEOUT)
    for index, response in enumerate(response_iterator):
      if response.payload.type != messages_pb2.COMPRESSABLE:
        raise ValueError(
            'response body of invalid type %s!' % response.payload.type)
      if len(response.payload.body) != sizes[index]:
        raise ValueError(
            'response body of invalid size %d!' % len(response.payload.body))


class _Pipe(object):

  def __init__(self):
    self._condition = threading.Condition()
    self._values = []
    self._open = True

  def __iter__(self):
    return self

  def next(self):
    with self._condition:
      while not self._values and self._open:
        self._condition.wait()
      if self._values:
        return self._values.pop(0)
      else:
        raise StopIteration()

  def add(self, value):
    with self._condition:
      self._values.append(value)
      self._condition.notify()

  def close(self):
    with self._condition:
      self._open = False
      self._condition.notify()


def _ping_pong(stub):
  request_response_sizes = (31415, 9, 2653, 58979)
  request_payload_sizes = (27182, 8, 1828, 45904)

  with stub:
    pipe = _Pipe()
    response_iterator = stub.FullDuplexCall(pipe, _TIMEOUT)
    print 'Starting ping-pong with response iterator %s' % response_iterator
    for response_size, payload_size in zip(
        request_response_sizes, request_payload_sizes):
      request = messages_pb2.StreamingOutputCallRequest(
          response_type=messages_pb2.COMPRESSABLE,
          response_parameters=(messages_pb2.ResponseParameters(
              size=response_size),),
          payload=messages_pb2.Payload(body=b'\x00' * payload_size))
      pipe.add(request)
      response = next(response_iterator)
      if response.payload.type != messages_pb2.COMPRESSABLE:
        raise ValueError(
            'response body of invalid type %s!' % response.payload.type)
      if len(response.payload.body) != response_size:
        raise ValueError(
            'response body of invalid size %d!' % len(response.payload.body))
    pipe.close()


def test_interoperability(test_case, stub):
  if test_case == 'empty_unary':
    _empty_unary(stub)
  elif test_case == 'large_unary':
    _large_unary(stub)
  elif test_case == 'server_streaming':
    _server_streaming(stub)
  elif test_case == 'client_streaming':
    _client_streaming(stub)
  elif test_case == 'ping_pong':
    _ping_pong(stub)
  else:
    raise NotImplementedError('Test case "%s" not implemented!')
