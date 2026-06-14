import { useEffect, useRef, useState } from "react"

interface MessageInputProps {
    onSend: (text: string) => void
}

export default function MessageInput({ onSend }: MessageInputProps) {
    const [text, setText] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    
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

    useEffect(() => {
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = `${textarea.scrollHeight}px`;
        }
    }, [text])

    return (
        <div className="bg-zinc-900 rounded-t-2xl rounded-b-none p-4 pb-8 flex flex-col items-end gap-3 w-full">
            <textarea 
                className="w-full resize-none overflow-hidden bg-transparent p-2 text-zinc-100 placeholder-zinc-500 focus:outline-none"
                ref={textareaRef}
                id="message" 
                value={text} 
                onChange={handleChange} 
                placeholder="Type something here..." 
                rows={1}/>
            <button 
                className="bg-purple-600 text-white font-medium py-2 px-4 rounded-full flex items-center justify-center hover:bg-purple-700 transition-colors" 
                onClick={handleSend}>
                Send
            </button>
        </div>
    )
}