import { useState } from "react"

const ALLOWED_TYPES = new Set([".pdf", ".docx", ".txt", ".md"]);

export default function BrowseButton() {
  const [files, setFiles] = useState<FileList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<string[]>([]);

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
          if (message === "COMPLETE") break
          setProgress(prev => [...prev, message]);
        }
      }

    } catch(error) {
      console.log("Submission Failed:", error);
    }
  }

  const canUpload = files !== null && error == null;

  return (
    <div>
      <input type="file" onChange={handleFileChange} multiple/>
      {files && Array.from(files).map((file, index) =>
        <p key={index}>{file.name}</p>
      )}
      {error && <p>{error}</p>}
      <button disabled={!canUpload} onClick={() => handleUpload(files!)}>Upload</button>
      {progress && progress.map((message, index) =>
        <p key={index}>
          {message}
        </p>
      )}
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
