from ihaveasecret.secretstore import CipheredMessage

def test_ciphered_message():
    message = CipheredMessage.create_from_message("password", "this is a test")
    assert message.decrypt("password") == "this is a test"

def test_wrong_password():
    try:
        message = CipheredMessage.create_from_message("password", "this is a test")
        message.decrypt("wrong password")
        assert False, "Exception not raised"
    except ValueError as e:
        pass