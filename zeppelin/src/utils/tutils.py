from .tools import Tools

def test_data_id(text):
    id = Tools.get_data_id(text)
    print(f'{text}={id}')

def test_tools():
    test_data_id('')
    test_data_id('abc')
    test_data_id('abc[x')
    test_data_id('abc]1')
    test_data_id('abc [] 22')
    test_data_id('abc [x] 22')
    test_data_id('abc [x-]')
    test_data_id('abc [-x]')
    test_data_id('abc [x-1]z')
    test_data_id('abc [x-2]')
    test_data_id('abc[x-3]')
    test_data_id('L1 [ABC-Vh]')
    test_data_id('Laveuse [LAL-W]')
    test_data_id('Sécheuse [SEC-KW]')


test_tools()