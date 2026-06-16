import { useState, useEffect } from "react";

const ALLOWED_TYPES = new Set([".pdf", ".docx", ".txt", ".md"]);

interface onUploadComplete {
    onUpload: (upload: boolean) => void;
}

export default function BrowseButton({ onUpload }: onUploadComplete) {
  const [files, setFiles] = useState<FileList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<string[]>([]);
  const [, setSessionId ] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);

  function handleDragOver(e: React.DragEvent<HTMLLabelElement>) {
    e.preventDefault()
    setIsDragging(true)
  }

  function handleDragLeave() {
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent<HTMLLabelElement>) => {

    setIsDragging(false);
    e.preventDefault()

    if (e.dataTransfer?.files) {
      const fileArray: FileList = e.dataTransfer.files

      const result = validateFiles(fileArray)

      if (result !== null) {
        setError(result);
        return;
      } else {
        setFiles(fileArray)
      }
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files;
    if (!selected) return;
    const result = validateFiles(selected);

    if (result !== null) {
      setError(result);
      return;
    } else {
      setFiles(selected);
    }
  }

  async function handleUpload(files: FileList) {

    setIsUploading(true)

    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }

    try {
      const response = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData,
        credentials: "include",
      });

      console.log(response); // Debugging message

      if (!response.ok) {
        const errorData = await response.json() //Debug message
        console.log(errorData) //Debug Message
        setError("Upload Failed");
        return;
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value);

        const lines = text.split("\n").filter(line => line.startsWith("data: "));
        for (const line of lines) {
          const message = line.replace("data: ", "");
          if (message === "COMPLETE") {
            onUpload(true)
            break
          }
        
          setProgress(prev => [...prev, message]);
        }
      }

    } catch(error) {
      console.log("Submission Failed:", error);
    }
  }

  useEffect(() => {
    async function initSession() {

      try {
        let response = await fetch("/api/session/verify", {
          method: 'GET',
          credentials: "include"
        })

        let data = await response.json();
        const valid = data.valid

        if (valid) {
          let sess_id = data.session_id
          setSessionId(sess_id)
        } else {
          response = await fetch("/api/session/create", {
            method: "POST",
            credentials: "include"
          })

          data = await response.json()
          let sess_id = data.session_id

          setSessionId(sess_id)
        }
      } catch (error) {
        console.log(`[SESSION] Something went wrong...${error}`)
      }
    }
    initSession()
  }, [])

  function FileIcon(props: React.SVGProps<SVGSVGElement>) {
    return (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="40"
        height="40"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-purple-400 shrink-0"
        {...props}
      >
        <path d="M14 2H7a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7z" />
        <path d="M14 2v5h5" />
        <path d="M9 13h6" />
        <path d="M9 17h6" />
      </svg>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col items-center justify-center p-4">
      <div className="flex flex-col items-center justify-center w-full max-w-xl text-center border-2 rounded-2xl border-purple-600 p-8">
        <h1 className="text-white text-4xl p-4">
          Welcome to
          <span className="block font-bold text-purple-600">
            DocAnalyze
          </span>
        </h1>
        <label 
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          htmlFor="file-upload"
          className={`cursor-pointer rounded-2xl border-2 border-dashed flex p-3 flex-col items-center relative justify-center bg-zinc-900/40 w-full min-h-[300px] transition-colors ${
            isDragging
              ? 'border-purple-400 bg-purple-950/20 shadow-lg shadow-purple-500/10'
              : 'border-purple-600'  
            }`}
          >
          {!files && !isUploading && (
            <div className="pointer-events-none flex flex-col items-center space-y-4 text-center">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-12 h-12 text-purple-400">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5h10.5a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0017.25 4.5H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25z" />
              </svg>
              <h2 className="text-neutral-300 text-xl font-medium">
                Choose a file or drag & drop it here
              </h2>
              <h3 className="text-neutral-700 text-xl font-small">
                JPEG, PNG, PDF and DOCX formats, up to 200MB
              </h3>

            </div>
          )}

          {files && !isUploading && (
            <div className="pointer-events-none flex flex-col items-center space-y-4 text-center">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-12 h-12 text-purple-400">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5h10.5a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0017.25 4.5H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25z" />
              </svg>
              <h2 className="text-neutral-300 text-xl font-medium">
                Choose a file or drag & drop it here
              </h2>
              <h3 className="text-neutral-700 text-xl font-small">
                JPEG, PNG, PDF and DOCX formats, up to 200MB
              </h3>

            </div>
          )}

          {isUploading && (
            <div className="w-full max-w-md mx-auto space-y-2 text-center pointer-events-none">
              {progress && progress.map((message, index) =>
                <p key={index} className="font-mono text-xs text-purple-300 animate-pulse">
                  {message}
                </p>
              )}
            </div>
          )}
          <input className="hidden" id="file-upload" type="file" onChange={handleFileChange} multiple/>
        </label>
        {files && !isUploading && (
          <div className="relative space-y-2 w-full text-center py-3">
            {files && Array.from(files).map((file) =>
              <div className="rounded-2xl border-2 flex flex-row items-center relative justify-left border-purple-600 bg-zinc-900/40 w-full min-h-[75px] transition-colors pl-2">
                <FileIcon className="w-10 h-10 p-1 text-purple-400 shrink-0"/>
                <h2 className="text-zinc-200 text-l font-medium truncate text-bold">
                  {file.name}
                </h2>
              </div>
            )}
            {error && <p className="text-rose-500 text-sm font-semibold mt-2">{error}</p>}
            <button className="cursor-pointer bg-purple-600 hover:bg-purple-500 text-white font-semibold py-2 px-6 rounded-lg transition-colors" 
              onClick={(e) => {
                e.stopPropagation();
                handleUpload(files!)}}>
                Go
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function validateFiles(files: FileList): (string | null) {
  let total_size: number = 0;
  for (const file of files) {
    const ext = "." + file.name.split(".").pop();
    if (!ALLOWED_TYPES.has(ext)) {
      return `${file.name} is not a supported file type.`
    }
    total_size += file.size;
  }

  if (total_size > 200 * 1024 * 1024) {
    return "Total size exceeds 200MB";
  }

  return null;
}
