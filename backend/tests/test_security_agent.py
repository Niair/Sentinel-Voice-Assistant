import sys
sys.path.insert(0, '.')
from app.agents.security_agent import get_security_agent
agent = get_security_agent()
print(f'Qwen2-VL-7B Security Agent loaded successfully!')
print(f'Model: {agent.model_name}')
print(f'Device: {agent.device}')
if hasattr(agent, 'analyze'):
    print(f'Analysis function exists')
else:
    print(f'No analysis function found')
    import inspect
    methods = [m for m in dir(agent) if not m.startswith('_\u0027) and callable(getattr(agent, m))]
    print(f'Available methods: {methods}')
    # Test with dummy image
    from PIL import Image
    import io
    try:
        test_image = Image.new('RGB', (640, 480), color = (73, 109, 137))
        img_byte_arr = io.BytesIO()
        test_image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        print(f'Testing with dummy image...')
        for method in methods:
            if method.startswith('analyze'):
                print(f'Found analysis method: {method}')
                try:
                    result = getattr(agent, method)(img_byte_arr, 'Is there a person?')
                    print(f'Result: {result}')
                except Exception as e:
                    print(f'Error: {e}')
    except Exception as e:
        print(f'Image test error: {e}')
