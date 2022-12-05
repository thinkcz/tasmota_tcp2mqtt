import paho.mqtt.client as mqtt  #import the client
import sys,os,binascii
import socket
import time


MQTT_BROKER = "81.28.13.115"

LOCAL_PORT  = 10007
REMOTE_PORT = 8291
REMOTE_IP   = "192.168.88.1"

TASMOTA_NAME = "demo-switch"

connection = None

def on_log(client, userdata, level, buf):
    print("log: ",buf)

def init_client_object():  
    mqtt.Client.bad_connection_flag=False
    mqtt.Client.suback_flag=False
    mqtt.Client.connected_flag=False
    mqtt.Client.disconnect_flag=False


def create_client(cname,clean_session=True):
    #flags set
    client= mqtt.Client(cname)
#      client.on_log=on_log
    client.on_connect= on_connect        #attach function to callback
    client.on_message=on_message        #attach function to callback
    client.on_subscribe=on_subscribe
    return client

def on_message(client, userdata, message):
    #time.sleep(1)
    
    topic=message.topic
    msg = str(message.payload.decode("utf-8"))
    print("[>] MQTT: ",topic, msg)
    
    if 'TCPABORT' in topic:
        if  client.tcpconn:
            client.tcpconn.close()

    if 'TCPRECIEVE' in topic:
        if  client.tcpconn:    
            br = bytearray.fromhex(msg)            
            client.tcpconn.sendall(br)
                
    if 'RESULT' in topic and '{"TCPConnect":' in msg:
         print ("[*] MQTT: proxy new connection")    


def on_connect(client, userdata, flags, rc):
    if rc==0:
        client.connected_flag=True
    else:
        client.bad_connection_flag=True
        if rc==5:
            print("[!] MQTT: broker requires authentication")

def on_subscribe(client, userdata, mid, granted_qos):
    print("[*] MQTT: Subscribed!")
    client.suback_flag=True            

def on_publish(client, userdata, mid):
    #print("message published ")
    pass

if __name__ == "__main__":

    if len(sys.argv)!=6:
        print("Usage:")
        print("mqttproxy mqttserver local_port remote_ip remote_port tasmota_name")
        sys.exit(1)
    

    try:
        MQTT_BROKER = sys.argv[1]
        LOCAL_PORT  = int(sys.argv[2])
    
        REMOTE_PORT  = int(sys.argv[4])    
        REMOTE_IP   = sys.argv[3]

        TASMOTA_NAME = sys.argv[5]
    except:
        print ("wrong parameters!")
        
    
    init_client_object()
    client= create_client("tcp2proxymqtt4545")

    try:
        res=client.connect(MQTT_BROKER,1883)
    except:
        print("[!] MQTT: cannot connect to broker")
        sys.exit()


    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    port = LOCAL_PORT
    server_address = ('localhost', port)
    print ('[*] TCP: starting up on %s port %s' % server_address, port)
    sock.bind(server_address)


    client.subscribe(f"+/{TASMOTA_NAME}/#")

    client.loop_start()

    #while True:
    #    time.sleep(1)


    sock.listen(1)
    # IP LISTENER
    while True:
        # Wait for a connection
        print ('[*] TCP: waiting for a connection')
        connection, client_address = sock.accept()
        try:
            print ('[>] TCP: connection from', client_address)
            print (f"[>] MQTT2TCP: connecting to {REMOTE_IP}:{REMOTE_PORT}")
            # connecting through MQTT
            client.publish(f"cmnd/{TASMOTA_NAME}/TCPConnect", f"{REMOTE_IP}:{REMOTE_PORT}")
            client.tcpconn = connection
            # Receive the data in small chunks and retransmit it
            while True:
                    data = connection.recv(16)
                    print ('[>] TCP: received "%s"' % data)
                    if data:
                        print('[<] TCP: sending data back to the client')
                        client.publish(f"cmnd/{TASMOTA_NAME}/TCPSend", binascii.hexlify((data)).upper())
                    else:
                        print ( '[*] TCP: no more data.')
                        client.publish(f"cmnd/{TASMOTA_NAME}/TCPClose")
                        break
                #except Exception as e:
                #    print(str(e))
                #    break
        finally:
            # Clean up the connection
            connection.close()
            client.tcpconn = None