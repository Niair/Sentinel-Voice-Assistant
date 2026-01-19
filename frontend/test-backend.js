async function testBackend() {
      console.log('Testing backend on http://localhost:8000/api/chat...');
      try {
            const response = await fetch('http://localhost:8000/api/chat', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                        messages: [{ role: 'user', content: 'Hi' }],
                        id: 'test-id-' + Date.now(),
                        user_id: '00000000-0000-0000-0000-000000000000'
                  }),
            });

            console.log('Status:', response.status);
            if (response.ok) {
                  const reader = response.body.getReader();
                  const decoder = new TextDecoder();
                  console.log('Streaming response:');
                  while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;
                        console.log(decoder.decode(value));
                  }
            } else {
                  console.log('Error:', await response.text());
            }
      } catch (err) {
            console.error('Backend unreachable:', err.message);
      }
}

testBackend();
