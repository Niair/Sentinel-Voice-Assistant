import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const url = new URL(request.url);
    const threadId = url.searchParams.get('thread_id') || 'default_thread';
    const formData = await request.formData();
    const file = formData.get('file') as File;

    if (!file) {
      return NextResponse.json({ error: 'No file uploaded' }, { status: 400 });
    }

    // Forward to FastAPI backend
    const backendFormData = new FormData();
    backendFormData.append('file', file);

    const response = await fetch(`http://localhost:8000/api/process-document?thread_id=${encodeURIComponent(threadId)}`, {
      method: 'POST',
      body: backendFormData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json({ error: errorData.detail || 'Failed to process document' }, { status: response.status });
    }

    const data = await response.json();
    
    // Return a mock URL for frontend preview if needed, 
    // but the backend now has the document in its RAG state.
    return NextResponse.json({
      url: `/api/files/placeholder/${data.filename}`,
      pathname: data.filename,
      contentType: 'application/pdf',
      success: true
    });
  } catch (error) {
    console.error('Upload error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
