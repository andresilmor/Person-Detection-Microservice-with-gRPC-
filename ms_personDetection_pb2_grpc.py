# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import ms_personDetection_pb2 as ms__personDetection__pb2


class PersonDetectionServerStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.inference = channel.unary_unary(
                '/PersonDetectionServer/inference',
                request_serializer=ms__personDetection__pb2.PersonDetectionRequest.SerializeToString,
                response_deserializer=ms__personDetection__pb2.PersonDetectionInferenceReply.FromString,
                )


class PersonDetectionServerServicer(object):
    """Missing associated documentation comment in .proto file."""

    def inference(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_PersonDetectionServerServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'inference': grpc.unary_unary_rpc_method_handler(
                    servicer.inference,
                    request_deserializer=ms__personDetection__pb2.PersonDetectionRequest.FromString,
                    response_serializer=ms__personDetection__pb2.PersonDetectionInferenceReply.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'PersonDetectionServer', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class PersonDetectionServer(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def inference(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/PersonDetectionServer/inference',
            ms__personDetection__pb2.PersonDetectionRequest.SerializeToString,
            ms__personDetection__pb2.PersonDetectionInferenceReply.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)