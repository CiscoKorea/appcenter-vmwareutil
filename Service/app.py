from flask import Flask, request, render_template, make_response, redirect
import json
from vmware_util import VMWareUtil
import sqlite3
from flask import g
import logging
from logging.handlers import RotatingFileHandler
# set the project root directory as the static folder, you can set others.

DATABASE = '/home/app/data/vmware.db'
vmware = None
hosts = None

app = Flask(__name__, static_url_path='')

@app.route('/index.html')
def root():
    global vmware
    logging.info('default /, redirect based-on vmware account database')
    with app.app_context():
        entry = query_db('select vcenter,username,password from vmware', one=True)
        if not vmware:
            if entry:
                vmware = VMWareUtil( entry['vcenter'], entry['username'], entry['password'])
                vmware.check_connectivity()
                return app.send_static_file('index.html')
            else:
                logging.info('redirect to vmware account registration page')
                return render_template('reg.html', user={'message': 'no exsting account info'})
        return app.send_static_file('index.html')
    

@app.route('/reg.json', methods=['POST', 'GET'])
def handle_reg():
    global vmware, hosts
    resp={ 'status': 'Error'}
    logging.info('GET /reg with new vmware account, redirect to app.html')
    if request.method == 'GET' :
        vcenter = request.values.get('vcenter')
        username = request.values.get('username')
        passwd = request.values.get('password')
        row = ( 1, vcenter, username, passwd)
        logging.info('argument (%s, %s, %s)' %(vcenter, username, passwd))
        with app.app_context():
            db = get_db()
            c = db.cursor()
            c.execute('delete from vmware')
            c.execute( 'insert into vmware values(?,?,?,?)', row)
            db.commit()
        vmware = None
        vmware = VMWareUtil( vcenter, username, passwd)
        hosts = None
        logging.info('Save vmware account & re-connecting vmware vcenter')
        if vmware :
            resp['status'] = 'OK'
        else:
            resp['status'] = 'Failed to connecting VMWare vCenter ... '
    return json.dumps( resp)



@app.route('/hosts.json')
def get_hosts():
    global vmware, hosts
    hosts = vmware.getHosts()
    return hosts

@app.route('/vms.json')
def get_vms():
    try:
        logging.info('GET /vms request')
        return vmware.getInventory()
    except :
        return json.dumps( {} )

@app.route('/portgroups.json')
def get_portgroups():
    global vmware, hosts
    host = request.args.get('host')
    logging.info('GET /portgroups.json?host= request')
    if not hosts :
        hosts = vmware.getHosts()
    nets = hosts[host]['nets']
    return json.dumps( nets)

@app.route('/vm.json')
def update_portgroup():
    global vmware, hosts
    uuid = request.args.get('uuid')
    portgroup = request.args.get('portgroup')
    logging.info('GET /vm.json?uuid=&portgroup= update VM PortGroup request')
    retval = vmware.reconfigureVM( uuid, portgroup)
    result = { 'status':'OK', 'message':'OK'}
    return json.dumps( result)

@app.route('/config.json')
def get_config():
    userinfo = { 'vcenter': '', 'username':'', 'password':''}
    userinfo['message'] = 'no existing account info'
    with app.app_context():
        entry = query_db('select vcenter,username,password from vmware', one=True)
        if entry:
            userinfo['vcenter'] = entry['vcenter']
            userinfo['username'] = entry['username']
            userinfo['password'] = entry['password']
            userinfo['message'] = 'loaded current account info'
    return json.dumps(userinfo)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

if __name__ == '__main__':
    global vmware, hosts
    # Setup logging
    fStr='%(asctime)s %(levelname)5s %(message)s'
    #handler = RotatingFileHandler('/home/app/log/vmware_util.log', maxBytes=10000, backupCount=1)
    #handler.setLevel( logging.DEBUG)
    #handler.setFormatter( logging.Formatter(fStr))
    #app.logger.addHandler(handler)
    logging.basicConfig(filename='/home/app/log/vmware_util.log', format=fStr, level=logging.DEBUG)
    #vmware = VMWareUtil('10.72.86.43', 'userid', 'passwd')
    vmware = None
    try:
        init_db()
    except:
        pass
    # Run app flask server
    app.run(host='0.0.0.0', port=80, debug=True)

