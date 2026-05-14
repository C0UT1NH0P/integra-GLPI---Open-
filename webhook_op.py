import os
import glpi
import pymysql
from dotenv import load_dotenv
from flask import Flask, jsonify, request

load_dotenv()

HOST_MYSQL=os.getenv('HOST_MYSQL')
PORT_MYSQL=os.getenv('PORT_MYSQL')
USER_MYSQL=os.getenv('USER_MYSQL')
PASS_MYSQL=os.getenv('PASS_MYSQL')
SCHEMA_MYSQL=os.getenv('SCHEMA_MYSQL')

app = Flask(__name__)

@app.route('/api/', methods=['GET', 'POST'])
def processar_atualizacao_de_pacote_de_trabalho():
    """Endpoint que recebe o webhook de atualização de pacote de trabalho do OpenProject. Avalia a prioridade no OpenProject e compara com o GLPI, se for diferente, atualiza no banco de dados e na API do GLPI.

    Returns:
        400: O tipo (work_package, project, ...) não é suportado.
        200: OK.
    """    
    data = request.get_json()
    print(data)
    if data is None:
        return jsonify({"error": "Invalid JSON or no JSON received"}), 400
    
    tipo_op = data.get("action").split(":")[0].strip()
    
    match tipo_op:
        case "work_package":    
            priority__id = data.get("work_package").get("_embedded").get("priority").get("id")
            
            work_package_id = data.get("work_package").get("id")
                        
            query = "SELECT " \
                    "prioridade_op " \
                "FROM " \
                    "integracao_chamados " \
                "WHERE " \
                    "id_op = %s " \
                    f"AND tipo_op = '{tipo_op}' "
            
            insert_query = """
                INSERT INTO integracao_chamados (id_op, tipo_op, prioridade_op)
                VALUES (%s, 'work_package', %s)
            """
            
            update_query = """
                UPDATE integracao_chamados
                SET prioridade_op = %s
                WHERE id_op = %s AND tipo_op = 'work_package'
            """
            
            chamado_id_query = "select id_glpi from integracao_chamados where id_op = %s and tipo_op = 'work_package'"
            
            with pymysql.connect(
                host=HOST_MYSQL,
                port=int(PORT_MYSQL),
                user=USER_MYSQL,
                password=PASS_MYSQL,
                database=SCHEMA_MYSQL
            ) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (work_package_id,))
                    result = cursor.fetchone()
                    print(result)
                    if result:
                        prioridade_op = result[0]
                        print(f"Prioridade OP: {prioridade_op}")
                        if prioridade_op != priority__id:
                            cursor.execute(update_query, (priority__id, work_package_id))
                            conn.commit()
                            print(f"Prioridade OP atualizada: {priority__id}")
                        else:
                            print("Prioridade OP não alterada")
                    else:
                        cursor.execute(insert_query, (work_package_id, priority__id))
                        conn.commit()
                        print(f"Prioridade OP inserida: {priority__id}")  
                        
                    id_chamado = cursor.execute(chamado_id_query, (work_package_id,))
                    id_chamado = cursor.fetchone()[0]
                    print(f"ID do chamado no GLPI: {id_chamado}") 
                     
            # Atualizar o chamado na API do GLPI
            glpi.update_ticket_priority(id_chamado, priority__id)
            
        case _:
            return jsonify({"error": "Tipo não suportado"}), 400
        
    return jsonify("OK"), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=30112)