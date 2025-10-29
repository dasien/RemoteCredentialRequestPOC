"""
Flask HTTP server for credential approval.

This module provides the RESTful API for agents to request credentials and
for the approval client to manage sessions. It delegates business logic to
PairingManager and focuses on HTTP routing and response formatting.

API Endpoints:
- GET  /health                 - Health check
- POST /pairing/initiate       - Generate pairing code
- POST /pairing/exchange       - PAKE message exchange
- POST /credential/request     - Request credential (encrypted)
- POST /session/revoke         - Revoke session
- GET  /session/status         - Check session status
"""
from flask import Flask, request, jsonify
import logging
from src.server.pairing_manager import PairingManager

logger = logging.getLogger(__name__)

# Create Flask app and pairing manager (module-level for import)
app = Flask(__name__)
pairing_manager = PairingManager()


@app.route('/health', methods=['GET'])
def health():
    """
    Server health check.

    Returns:
        JSON with status and active session count
    """
    return jsonify({
        "status": "ok",
        "active_sessions": pairing_manager.active_session_count()
    })


@app.route('/pairing/initiate', methods=['POST'])
def pairing_initiate():
    """
    Initiate pairing - generate pairing code.

    Request Body:
        {
            "agent_id": "flight-001",
            "agent_name": "Flight Agent"
        }

    Response:
        {
            "pairing_code": "847293",
            "expires_at": "2025-10-29T00:05:00Z"
        }

    Status Codes:
        200 - Success
        400 - Bad request (missing fields)
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Missing request body"}), 400

    agent_id = data.get('agent_id')
    agent_name = data.get('agent_name')

    if not agent_id or not agent_name:
        return jsonify({"error": "Missing agent_id or agent_name"}), 400

    pairing_code, expires_at = pairing_manager.create_pairing(agent_id, agent_name)

    logger.info(f"Pairing initiated for {agent_name} ({agent_id}): {pairing_code}")

    return jsonify({
        "pairing_code": pairing_code,
        "expires_at": expires_at.isoformat() + "Z"
    })


@app.route('/pairing/exchange', methods=['POST'])
def pairing_exchange():
    """
    Execute PAKE protocol message exchange.

    Request Body:
        {
            "pairing_code": "847293",
            "pake_message": "<base64-encoded SPAKE2_A message>"
        }

    Response (user hasn't entered code yet):
        {"status": "waiting"}
        Status: 202 Accepted

    Response (success):
        {
            "session_id": "sess_abc123...",
            "pake_message": "<base64-encoded SPAKE2_B message>",
            "agent_id": "flight-001"
        }
        Status: 200 OK

    Response (error):
        {"error": "Invalid pairing code"}
        Status: 400 Bad Request

    Status Codes:
        200 - PAKE exchange complete, session established
        202 - Waiting for user to enter code
        400 - Invalid/expired pairing code or missing fields
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Missing request body"}), 400

    pairing_code = data.get('pairing_code')
    msg_in_a = data.get('pake_message')  # base64-encoded

    if not pairing_code or not msg_in_a:
        return jsonify({"error": "Missing pairing_code or pake_message"}), 400

    # Delegate to pairing manager
    result = pairing_manager.exchange_pake_message(pairing_code, msg_in_a)

    if result['status'] == 'waiting':
        # User hasn't entered code yet (agent should poll)
        return jsonify({"status": "waiting"}), 202

    elif result['status'] == 'success':
        # PAKE exchange complete, session established
        logger.info(f"PAKE exchange successful, session: {result['session_id']}")
        return jsonify({
            "session_id": result['session_id'],
            "pake_message": result['pake_message'],  # base64-encoded SPAKE2_B
            "agent_id": result['agent_id']
        })

    else:
        # Error (expired, invalid, etc.)
        logger.warning(f"PAKE exchange failed: {result.get('error')}")
        return jsonify({"error": result['error']}), 400


@app.route('/credential/request', methods=['POST'])
def credential_request():
    """
    Request credential (encrypted).

    Request Body:
        {
            "session_id": "sess_abc123...",
            "encrypted_payload": "<base64-encoded encrypted request>"
        }

    Encrypted Payload (decrypted by server):
        {
            "domain": "aa.com",
            "reason": "Login to American Airlines",
            "agent_id": "flight-001",
            "agent_name": "Flight Agent",
            "timestamp": "2025-10-29T00:00:00Z",
            "nonce": "a1b2c3d4..."
        }

    Response (approved):
        {
            "status": "approved",
            "encrypted_payload": "<base64-encoded encrypted credential>"
        }

    Response (denied):
        {
            "status": "denied",
            "error": "User denied"
        }

    Response (error):
        {
            "status": "error",
            "error": "Session expired"
        }

    Status Codes:
        200 - Request processed (approved/denied/error in response body)
        400 - Bad request (missing fields)
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Missing request body"}), 400

    session_id = data.get('session_id')
    encrypted_payload = data.get('encrypted_payload')

    if not session_id or not encrypted_payload:
        return jsonify({"error": "Missing session_id or encrypted_payload"}), 400

    # Delegate to pairing manager (which will prompt user and retrieve credential)
    result = pairing_manager.handle_credential_request(session_id, encrypted_payload)

    if result['status'] == 'approved':
        logger.info(f"Credential request approved for session: {session_id}")
    elif result['status'] == 'denied':
        logger.info(f"Credential request denied for session: {session_id}")
    else:
        logger.warning(f"Credential request error for session: {session_id} - {result.get('error')}")

    return jsonify(result)


@app.route('/session/revoke', methods=['POST'])
def session_revoke():
    """
    Revoke session.

    Request Body:
        {"session_id": "sess_abc123..."}

    Response:
        {
            "revoked": true,
            "session_id": "sess_abc123..."
        }

    Status Codes:
        200 - Success
        400 - Bad request (missing session_id)
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Missing request body"}), 400

    session_id = data.get('session_id')

    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400

    pairing_manager.revoke_session(session_id)

    logger.info(f"Session revoked via API: {session_id}")

    return jsonify({"revoked": True, "session_id": session_id})


@app.route('/session/status', methods=['GET'])
def session_status():
    """
    Check session status.

    Query Parameters:
        session_id: Session identifier

    Response:
        {
            "active": true,
            "agent_name": "Flight Agent",
            "last_access": "2025-10-29T00:10:00Z",
            "expires_at": "2025-10-29T00:30:00Z"
        }

    Status Codes:
        200 - Success
        400 - Bad request (missing session_id)
        404 - Session not found
    """
    session_id = request.args.get('session_id')

    if not session_id:
        return jsonify({"error": "Missing session_id parameter"}), 400

    status = pairing_manager.get_session_status(session_id)

    if not status:
        return jsonify({"error": "Session not found"}), 404

    return jsonify(status)


def run_server(host='127.0.0.1', port=5000):
    """
    Run approval server.

    Args:
        host: Host to bind to (default: 127.0.0.1)
        port: Port to bind to (default: 5000)
    """
    logger.info(f"Starting approval server on {host}:{port}")

    # CRITICAL FIX: Disable werkzeug request logging
    # This prevents log spam from polling requests making Terminal 1 unusable
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.ERROR)  # Only show errors, not every request

    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    # Setup logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    run_server()