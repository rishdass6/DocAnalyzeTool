import { useState } from "react"

interface MessageInputProps {
    onSend: (text: string) => void
}

export default function MessageInput({ onSend }: MessageInputProps) {
    const [text, setText] = useState('');
    
    function handleSend() {
        if (text.trim() == '') {
            return
        }

        onSend(text)

        setText('')
    }

    const handleChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
        setText(event.target.value)
    };



    return (
        <div>
            <label htmlFor="message">Your Message:</label>
            <textarea id="message" value={text} onChange={handleChange} placeholder="Type something here..." rows={5} cols={40}/>
            <button onClick={handleSend}>Send</button>
        </div>
    )
}