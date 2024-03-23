from ihaveasecret.secretstore import encode_message, decode_message, secretStore

def test_encode_message():
    message = "this is a test"
    password = "password"
    encoded = encode_message(password, message)
    assert message != encoded
    assert message == decode_message(password, encoded)
