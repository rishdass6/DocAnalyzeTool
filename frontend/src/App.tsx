import { useEffect, useState } from "react"
import ChatPanel from "./chat/ChatPanel";
import BrowseButton from "./BrowseButton";

export default function App() {
  const [ uploadS, setUploadS ] = useState<boolean>();

  const handleUploadComplete = (upload: boolean) => {
    setUploadS(upload)
  }

  return (
    <div>
      <BrowseButton onUpload={handleUploadComplete} />
      {uploadS && <ChatPanel />}
    </div>
  )
}