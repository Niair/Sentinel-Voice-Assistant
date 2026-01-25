import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const url = new URL(request.url);
    const threadId = url.searchParams.get("thread_id") || "default_thread";
    const formData = await request.formData();
    const file = formData.get("file") as File;

    if (!file) {
      return NextResponse.json({ error: "No file uploaded" }, { status: 400 });
    }

    const backendFormData = new FormData();
    backendFormData.append("file", file);

    const response = await fetch(
      `http://localhost:8000/api/process-document?thread_id=${encodeURIComponent(threadId)}`,
      { method: "POST", body: backendFormData }
    );

    if (!response.ok) {
      let detail = "Failed to process document";
      try {
        const errorData = (await response.json()) as { detail?: string };
        detail = errorData.detail ?? detail;
      } catch {
        /* non-JSON body */
      }
      return NextResponse.json({ error: detail }, { status: response.status });
    }

    const data = (await response.json()) as { filename?: string };

    return NextResponse.json({
      url: `/api/files/placeholder/${data.filename}`,
      pathname: data.filename,
      contentType: "application/pdf",
      success: true,
    });
  } catch (error) {
    console.error("Upload error:", error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
