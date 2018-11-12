from flask import Flask, request, session, render_template, redirect, url_for
from flask import _request_ctx_stack as stack
import requests
import sys
import phases_pb2
import phases_pb2_grpc
import argparse
from jaeger_client import Tracer, ConstSampler
from jaeger_client.reporter import NullReporter
from jaeger_client.codecs import B3Codec
from opentracing.ext import tags
from opentracing.propagation import Format
from opentracing_instrumentation.request_context import get_current_span, span_in_context
from argparse import ArgumentParser

import grpc

app = Flask(__name__) 

tracer = Tracer(
    one_span_per_rpc=True,
    service_name='productpage',
    reporter=NullReporter(),
    sampler=ConstSampler(decision=True),
    extra_codecs={Format.HTTP_HEADERS: B3Codec()}
)


print("starting moon site")
parser = ArgumentParser()
parser = argparse.ArgumentParser()
parser.add_argument("phases", nargs='?')
parser.add_argument("facts", nargs='?')

args = parser.parse_args()

# source:
# https://github.com/istio/istio/blob/master/samples/bookinfo/src/productpage/productpage.py
def trace():
    '''
    Function decorator that creates opentracing span from incoming b3 headers
    '''
    def decorator(f):
        def wrapper(*args, **kwargs):
            request = stack.top.request
            try:
                # Create a new span context, reading in values (traceid,
                # spanid, etc) from the incoming x-b3-*** headers.
                span_ctx = tracer.extract(
                    Format.HTTP_HEADERS,
                    dict(request.headers)
                )
                rpc_tag = {tags.SPAN_KIND: tags.SPAN_KIND_RPC_SERVER}
                span = tracer.start_span(
                    operation_name='op', child_of=span_ctx, tags=rpc_tag
                )
            except Exception as e:
                span = tracer.start_span('op')
            with span_in_context(span):
                r = f(*args, **kwargs)
                return r
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator


def getForwardHeaders(request):
    headers = {}
    if 'user' in session:
        headers['end-user'] = session['user']
    incoming_headers = [ 'x-request-id',
                         'x-b3-traceid',
                         'x-b3-spanid',
                         'x-b3-parentspanid',
                         'x-b3-sampled',
                         'x-b3-flags',
                         'x-ot-span-context'
    ]

    for ihdr in incoming_headers:
        val = request.headers.get(ihdr)
        if val is not None:
            headers[ihdr] = val
            #print "incoming: "+ihdr+":"+val

    return headers


def getMoonFact(headers):
    print("Istio headers: ", headers)
    try:
        url = args.facts.split("=")[1]
        res = requests.get(url, headers=headers, timeout=3.0)
    except:
        res = None
    if res and res.status_code == 200:
        return 200, res.text
    else:
        status = res.status_code if res is not None and res.status_code else 500
        return status, 'Error: could not reach MoonFacts HTTP server'


def getMoonPhase(headers):  
    print("trying to get moon phase...")
    tup = ((k, v) for k, v in headers.iteritems())
    print("istio headers as nested tuple: ", tup)
    try:
        g = args.phases.split("=")[1] 
        channel = grpc.insecure_channel(g)
        stub = phases_pb2_grpc.MoonPhasesStub(channel)
        res = stub.GetPhases(request=phases_pb2.GetPhasesRequest(), metadata=tup)
    except:
        res = None
    if res and res.status_code == 200:
        return 200, res.PhaseInfo 
    else:
        status = res.status_code if res is not None and res.status_code else 500
        return status, phases_pb2.PhaseInfo()


@app.route('/')
@trace()
def homepage():
    headers = getForwardHeaders(request) 
    fact = getMoonFact(headers) 
    phaseInfo = getMoonPhase(headers)
    return render_template('index.html', p=phaseInfo, fact=fact)


if __name__=='__main__': 
    app.run(debug=True, host='0.0.0.0')