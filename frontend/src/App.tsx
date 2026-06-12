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
      {!uploadS ? <BrowseButton onUpload={handleUploadComplete} /> : <ChatPanel/>}
    </div>
  )
}