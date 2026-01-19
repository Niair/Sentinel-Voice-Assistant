import { NextResponse } from 'next/server';

export async function POST(request: Request) {
      // Mock file upload for now to prevent errors
      return NextResponse.json({
            url: '/placeholder.png',
            pathname: 'placeholder.png',
            contentType: 'image/png'
      });
}
