from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, create_refresh_token, get_jwt_identity
import psycopg2
from datetime import timedelta, datetime
import os
from dotenv import load_dotenv
load_dotenv()

NOT_FOUND_CODE = 400
OK_CODE = 200
SUCCESS_CODE = 201
BAD_REQUEST_CODE = 400
UNAUTHORIZED_CODE = 401
FORBIDDEN_CODE = 403
NOT_FOUND = 404
SERVER_ERROR = 500

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.getenv('KEY_API')
# Define a expiração dos Tokens
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=5)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(hours=12)

jwt = JWTManager(app)

## Test
@app.route('/', methods = ["GET"])
def home():
    return "Bem vindo à API!", OK_CODE


## Auth
@app.route('/login', methods=['POST'])
def login():
    content = request.get_json()
    
    if 'username' not in content or 'password' not in content:
        return jsonify({'msg': 'Parametros invalidos'}), BAD_REQUEST_CODE
    
    username = content['username']
    password = content['password']
    
    get_info = "SELECT * from tam.login_user(%s,%s);"
    
    values = [username, password]
    
    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(get_info, values)
                row = cursor.fetchone()
                print(row)
                if len(row) > 0:
                    if row[0]:
                        # Se as credenciais estiverem corretas, cria um token de acesso com expiração definida
                        access_token = create_access_token(identity=row[0])
                        refresh_token = create_refresh_token(identity=row[0])
                        result = {"err": 0, 
                                "user": {
                                    "id": row[0], 
                                    "username": username, 
                                    "token": access_token,
                                    "refresh_token": refresh_token},
                                "msg": "Sucesso ao autenticar utilizador."}          
                    else:
                        result = {"err": 1, 
                              "msg": "Utilizador ou palavra-passe incorreta.",
                              "Error": "Credenciais invalidas."}
                else:
                    result = {"err": 1, 
                              "msg": "Utilizador ou palavra-passe incorreta.",
                              "Error": "Credenciais invalidas."}
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"err": -1, 
                        "msg": "Erro desconhecido.", 
                        "Error": str(error)
                        }), SERVER_ERROR
    
    return jsonify(result), OK_CODE


## Register
@app.route("/register", methods=['POST'])
def register():
    content = request.get_json()
    
    if 'username' not in content or 'password' not in content or 'email' not in content:
        return jsonify({'msg': 'Parametros invalidos'}), BAD_REQUEST_CODE
    
    username = content['username']
    password = content['password']
    email = content['email']
    
    result = None
    
    get_info = """SELECT tam.register_user(%s,%s,%s);"""
    values = [username, password, email]
    
    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(get_info, values)
                row = cursor.fetchone()
                # print(row)
                if row is not None:
                    user_id = row[0]
                    if user_id is not None:
                        # Se as credenciais estiverem corretas, cria um token de acesso com expiração definida
                        access_token = create_access_token(identity=user_id)
                        refresh_token = create_refresh_token(identity=user_id)
                        result = { 
                                "err": 0,
                                "user": {
                                    "id": user_id, 
                                    "username": username, 
                                    "token": access_token,
                                    "refresh_token": refresh_token}, 
                                "msg": "Sucesso ao adicionar utilizador."}
                    else:
                        result = { 
                                "err": 2,
                                "msg": "ID inválido."}
                else:
                    result = { 
                            "err": 2,
                            "msg": "Resultado inválido."}
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"err": -1, 
                        "msg": "Erro desconhecido.", 
                        "Error": str(error)
                        }), SERVER_ERROR
    
    return jsonify(result), OK_CODE


@app.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    # Se refresh token estiver válido, cria um token de acesso com expiração definida
    result = {
        "user": {
            "token": create_access_token(identity=current_user)
        }
    }
    return jsonify(result), OK_CODE


## List
@app.route('/list', methods=['GET'])
@jwt_required()
def list():
    current_user = get_jwt_identity()
    result = None
    
    ## TODO listar todos os eventos adicionando a informação se o user está inscrito ou não (NEW DB FUNCTION)
    # query = """SELECT list_events(%s);"""
    # values = [current_user]
    query = """ SELECT *  FROM tam.event; """
    values = []
    
    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, values)
                rows = cursor.fetchall()
                events = []
                print(rows)
                for event in rows:
                    if event[0] is not None:
                        
                        events.append({
                            'id': event[0],
                            'user_id': event[1],
                            'type': event[2],
                            'description': event[3],
                            'location': event[4],
                            'event_date': event[5].strftime("%d/%m/%Y"),
                            'event_time': event[6].strftime("%H:%M"),
                            'deadline_date': event[7].strftime("%d/%m/%Y"),
                            'deadline_time': event[8].strftime("%H:%M"),
                            'seats': event[9],
                            'price': event[10],
                            'has_subscribes': event[11]
                            # ,
                            # 'user_subscribed': event[12]
                        })
                        
                result = { 
                        "err": 0,
                        "msg": "Lista de eventos.",
                        "events": events}
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"err": -1, 
                        "msg": "Erro desconhecido.", 
                        "Error": str(error)
                        }), SERVER_ERROR
    
    return jsonify(result), OK_CODE


## Insert
@app.route('/add_event', methods=['POST'])
@jwt_required()
def add_event():
    current_user = get_jwt_identity()
    content = request.get_json()
    
    keys_and_types = {"type": str,"description": str,"location": str,
                      "event_date": str,"event_time": str,
                      "deadline_date": str,"deadline_time": str,
                      "seats": int,"price": float}
    # Verificação se todas as chaves necessárias estão presentes 
    for key, value_type in keys_and_types.items():
        if key not in content:
            return jsonify({'msg': 'Parametros invalidos'}), BAD_REQUEST_CODE
        else:
            if not isinstance(content[key], value_type):
                return jsonify({'msg': 'Parametros invalidos'}), BAD_REQUEST_CODE

    # Converter a string em um objeto de data (date)
    try:
        event_date = datetime.strptime(content["event_date"], "%d/%m/%Y").date()
        event_time = datetime.strptime(content["event_time"], "%H:%M").time()
        deadline_date = datetime.strptime(content["deadline_date"], "%d/%m/%Y").date()
        deadline_time = datetime.strptime(content["deadline_time"], "%H:%M").time()
    except ValueError:
        return jsonify({"msg": "Formato de data ou time incorreto"}), BAD_REQUEST_CODE

    query = """SELECT tam.add_event(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);"""
    values = [current_user,content["type"],content["description"],
              content["location"],event_date,event_time,
              deadline_date,deadline_time,
              content["seats"],content["price"]]
    
    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, values)
                # Recuperar o resultado retornado pela função
                row = cursor.fetchone()
                # print(row)
                if row is not None:
                    success = row[0]
                    if success is not None and success:
                        result = { 
                                "err": 0,
                                "success": success,
                                "msg": "Sucesso ao adicionar evento."}
                    else:
                        result = { 
                            "err": 1,
                            "success": False,
                            "msg": "Erro ao adicionar evento."}
                else:
                    result = { 
                            "err": 2,
                            "msg": "Resultado inválido."}
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"err": -1, 
                        "msg": "Erro desconhecido.", 
                        "Error": str(error)
                        }), SERVER_ERROR
    
    return jsonify(result), OK_CODE


## Subscribe
@app.route('/subscribe_event', methods=['POST'])
@jwt_required()
def subscribe_event():
    current_user = get_jwt_identity()
    content = request.get_json()
    
    keys_and_types = {"id_event": int}

    # Verificação se todas as chaves necessárias estão presentes 
    for key, value_type in keys_and_types.items():
        if key not in content:
            return jsonify({'msg': 'Parametros invalidos'}), BAD_REQUEST_CODE
        else:
            if not isinstance(content[key], value_type):
                return jsonify({'msg': 'Parametros invalidos'}), BAD_REQUEST_CODE

    query = """SELECT tam.subscribe_event(%s,%s);"""
    values = [current_user, content["id_event"]]
    
    result = None
    
    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, values)
                # Recuperar o resultado retornado pela função
                row = cursor.fetchone()
                # print(row)
                if row is not None:
                    success = row[0]
                    if success is not None and success:
                        result = { 
                                "err": 0,
                                "success": success,
                                "msg": "Inscrito."}
                    else:
                        result = { 
                            "err": 1,
                            "success": False,
                            "msg": "Erro ao inscrever em evento."}
                else:
                    result = { 
                            "err": 2,
                            "msg": "Resultado inválido."}
        conn.close()
        
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"err": -1, 
                        "msg": "Erro desconhecido.", 
                        "Error": str(error)
                        }), SERVER_ERROR
    
    return jsonify(result), OK_CODE


## Unsubscribe
@app.route('/unsubscribe_event', methods=['POST'])
@jwt_required()
def unsubscribe_event():
    current_user = get_jwt_identity()
    content = request.get_json()
    
    keys_and_types = {"id_event": int}

    # Verificação se todas as chaves necessárias estão presentes 
    for key, value_type in keys_and_types.items():
        if key not in content:
            return jsonify({'msg': 'Parametros invalidos'}), BAD_REQUEST_CODE
        else:
            if not isinstance(content[key], value_type):
                return jsonify({'msg': 'Parametros invalidos'}), BAD_REQUEST_CODE

    query = """SELECT tam.unsubscribe_event(%s,%s);"""
    values = [current_user, content["id_event"]]
    
    result = None
    
    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, values)
                # Recuperar o resultado retornado pela função
                row = cursor.fetchone()
                # print(row)
                if row is not None:
                    success = row[0]
                    if success is not None and success:
                        result = { 
                                "err": 0,
                                "success": success,
                                "msg": "Unsubscribed."}
                    else:
                        result = { 
                            "err": 1,
                            "success": False,
                            "msg": "Erro ao desinscrever em evento."}
                else:
                    result = { 
                            "err": 2,
                            "msg": "Resultado inválido."}
        conn.close()
        
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"err": -1, 
                        "msg": "Erro desconhecido.", 
                        "Error": str(error)
                        }), SERVER_ERROR
    
    return jsonify(result), OK_CODE


## Remove
@app.route('/delete_event/<int:id_event>', methods=['PATCH'])
@jwt_required()
def delete_event(id_event):
    current_user = get_jwt_identity()
    
    # Verificação se todas as chaves necessárias estão presentes
    if id_event is None:
        return jsonify({'msg': 'Parametros invalidos'}), BAD_REQUEST_CODE
    else:
        if not isinstance(id_event, int):
            return jsonify({'msg': 'Parametros invalidos'}), BAD_REQUEST_CODE
    
    result = None
    
    query = """SELECT tam.delete_event(%s, %s);"""
    values = [id_event, current_user]
    
    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, values)
                # Recuperar o resultado retornado pela função
                row = cursor.fetchone()
                # print(row)
                if row is not None:
                    success = row[0]
                    if success is not None and success:
                        result = { 
                            "err": 0,
                            "success": success,
                            "msg": "Evento removido."}
                    else:
                        result = { 
                            "err": 1,
                            "success": False,
                            "msg": "Erro ao remover evento."}
                else:
                    result = { 
                            "err": 2,
                            "msg": "Resultado inválido."}
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"err": -1, 
                        "msg": "Erro desconhecido.", 
                        "Error": str(error)
                        }), SERVER_ERROR
    
    return jsonify(result), OK_CODE


## Edit
@app.route('/edit_event', methods=['PATCH'])
@jwt_required()
def edit_event():
    current_user = get_jwt_identity()
    
    content = request.get_json()
    
    keys_and_types = {"id": int, "type": str,"description": str,"location": str,
                      "event_date": str,"event_time": str,
                      "deadline_date": str,"deadline_time": str,
                      "seats": int,"price": float}
    # Verificação se todas as chaves necessárias estão presentes 
    for key, value_type in keys_and_types.items():
        if key not in content:
            return jsonify({'msg': 'Parametros invalidos'}), BAD_REQUEST_CODE
        else:
            if not isinstance(content[key], value_type):
                return jsonify({'msg': 'Parametros invalidos'}), BAD_REQUEST_CODE
    
    result = None
    
    # Converter a string em um objeto de data (date)
    try:
        event_date = datetime.strptime(content["event_date"], "%d/%m/%Y").date()
        event_time = datetime.strptime(content["event_time"], "%H:%M").time()
        deadline_date = datetime.strptime(content["deadline_date"], "%d/%m/%Y").date()
        deadline_time = datetime.strptime(content["deadline_time"], "%H:%M").time()
    except ValueError:
        return jsonify({"msg": "Formato de data ou time incorreto"}), BAD_REQUEST_CODE

    result = None
    
    query = """SELECT tam.edit_event(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);"""
    values = [content["id"], current_user,content["type"],
              content["description"],content["location"],
              event_date,event_time,deadline_date,deadline_time,
              content["seats"],content["price"]]
    
    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, values)
                # Recuperar o resultado retornado pela função
                row = cursor.fetchone()
                # print(row)
                if row is not None:
                    success = row[0]
                    if success is not None and success:
                        result = { 
                            "err": 0,
                            "success": success,
                            "msg": "Evento atualizado."}
                    else:
                        result = { 
                            "err": 1,
                            "success": False,
                            "msg": "Erro ao atualizar evento."}
                else:
                    result = { 
                            "err": 2,
                            "msg": "Resultado inválido."}
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"err": -1, 
                        "msg": "Erro desconhecido.", 
                        "Error": str(error)
                        }), SERVER_ERROR
    
    return jsonify(result), OK_CODE


##########################################################
## DATABASE ACCESS
##########################################################
def db_connection():
    DATABASE_URL = os.getenv('CONECTION')
    return psycopg2.connect(DATABASE_URL)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)
