from flask import Flask
from cobra.mit.access import MoDirectory
from cobra.mit.session import CertSession
from cobra.mit.session import LoginSession
from cobra.model.pol import Uni as PolUni
from cobra.model.aaa import UserEp as AaaUserEp
from cobra.model.aaa import AppUser as AaaAppUser
from cobra.model.aaa import UserCert as AaaUserCert
from cobra.internal.codec.jsoncodec import toJSONStr, fromJSONStr
from cobra.internal.codec.xmlcodec import _toXMLStr, fromXMLStr

import json
import logging

app = Flask(__name__)

def createCertSession():
    ''' Creates a session with the APIC.
    Returns a CertSession (Cobra SDK) that can be used to query the APIC. 
    '''

    certUser = 'Cisco_VMWarePortGroupUtil2' # Format: <Vendordomain>_<AppId>
    pKeyFile = '/home/app/credentials/plugin.key' # Fixed for every app

    polUni = PolUni('')
    aaaUserEp = AaaUserEp(polUni)
    aaaAppUser = AaaAppUser(aaaUserEp, certUser)

    aaaUserCert = AaaUserCert(aaaAppUser, certUser)

    with open(pKeyFile, "r") as file:
        pKey = file.read()

    apicUrl = 'https://172.17.0.1/' # Fixed, APIC's gateway for the app

    session = CertSession(apicUrl, aaaUserCert.dn, pKey, secure=False)
    return session

def respFormatJsonMos(mos, totalCount):
    ''' Format a JSON reply from MOs.
    Inputs:
        - mos: array of MOs
        - totalCount: number of MOs

    Output:
        - JSON dictionary, following this format
        {  
           "imdata":[{<MO>}, {<MO>},...],
           "totalCount": ...
        }

    Example:
        {  
           "imdata":[  
              {  
                 "fvTenant":{  
                    "attributes":{  
                       "dn":"uni/tn-common",
                       ...
                    }
                 }
              },
              {  
                 "fvTenant":{  
                    "attributes":{  
                       "dn":"uni/tn-infra",
                       ...
                    }
                 }
              }
           ],
           "totalCount":"3"
        }
    '''
    jsonStr = '{"totalCount": "%s", "imdata": [' % totalCount
    first = True
    for mo in mos:
        if not first:
            jsonStr += ','
        else:
            first = False
        jsonStr += toJSONStr(mo, includeAllProps=True)
    jsonStr += ']}'
    jsonDict = json.loads(jsonStr)

    return json.dumps(jsonDict)

@app.route('/')
def hello_world():
    ''' Test the connectivity.
    '''
    logging.info('Received API Request from Client - /')
    return 'Cisco HelloACI PlugIn Version 1.0.'

@app.route('/getTenant.json')
def get_tenant():
    ''' Queries the APIC for tenants and replies with those tenants,
    in a JSON format.
    '''
    logging.info('Received API request from client, api: /getTenant.json')

    # Create session
    loginSession = createCertSession()

    # Create object to go through the MIT
    moDir = MoDirectory(loginSession)

    moDir.login()
    # Query for the tenants
    tenantMo = moDir.lookupByClass('fvTenant');
    moDir.logout()
    
    logging.info('Sending response')
    return respFormatJsonMos(tenantMo, tenantMo.totalCount)

if __name__ == '__main__':
    # Setup logging
    fStr='%(asctime)s %(levelname)5s %(message)s'
    logging.basicConfig(filename='/home/app/log/helloaci.log', format=fStr, level=logging.DEBUG)

    # Run app flask server
    app.run(host='0.0.0.0', port=80)
