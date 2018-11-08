from flask import Flask
from flask import render_template
import requests
import phases_pb2
import phases_pb2_grpc
import argparse
from argparse import ArgumentParser

import grpc

app = Flask(__name__)

print("starting moon site")
parser = ArgumentParser()
parser = argparse.ArgumentParser()
parser.add_argument("phases", nargs='?')
parser.add_argument("facts", nargs='?')

args = parser.parse_args()

@app.route('/')
def homepage():
    # get fun-fact  (Ruby HTTP)
    f = args.facts.split("=")[1]
    print(f)
    r = requests.get(f) 
    fact = r.text

    # get phase info (Go gRPC)
    g = args.phases.split("=")[1]
    with grpc.insecure_channel(g) as channel:
        stub = phases_pb2_grpc.MoonPhasesStub(channel)
        p = stub.GetPhases(phases_pb2.GetPhasesRequest())
        print(p.PhaseInfo.City)

    return render_template('index.html', city=p.PhaseInfo.City, lat=p.PhaseInfo.Lat, lon=p.PhaseInfo.Lon, rise=p.PhaseInfo.Rise, upperTransit=p.PhaseInfo.UpperTransit, set=p.PhaseInfo.Set, closestPhase=p.PhaseInfo.ClosestPhase,  fact=fact)


if __name__=='__main__':
    app.run(debug=True, host='0.0.0.0')