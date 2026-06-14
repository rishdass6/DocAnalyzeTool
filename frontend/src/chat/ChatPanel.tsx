import { useState } from "react";
import type { Message } from "./types";
import MessageInput from "./MessageInput";
import MessageList from "./MessageList";
import TypingIndicator from "./TypingIndicator";

export default function ChatPanel() {
    const [ messages, setMessages ] = useState<Message[]>([]);
    const [ aiResponse, setAiResponse ] = useState<boolean | null>(null);
    let time_taken: number = 0;

    async function handleSend(text: string) {

        setMessages((prevMessages) => [
            ...prevMessages,
            { author: "user", text: `${text}`},
            { author: "ai", text: "" }
        ])

        setAiResponse(true)

        const start_time = Date.now()

        const response = await fetch("/api/chat", {
            method: "POST",
            body: JSON.stringify({ query: text }),
            headers: { "Content-Type" : "application/json"},
            credentials: "include"
        })
        
        const reader = response.body!.getReader()
        const decoder = new TextDecoder()

        while(true) {
            const { done, value } = await reader.read()
            if (done) break;

            const chunk_text = decoder.decode(value);
            //const new_text = chunk_text.replace('data: ', "")
            const new_text = chunk_text.split("\n").filter(line => line.startsWith("data: "))

            for (const line of new_text) {
                const message = line.replace("data: ", "")
                if (message === "DONE") {
                    break;
                }

                setMessages(prev => {
                    const updated = [...prev]
                    updated[updated.length - 1] = {
                        author: "ai",
                        text: updated[updated.length - 1].text + message
                    }
                    return updated 

                }
            )}
        }

        const end_time = Date.now()

        setAiResponse(false)

        time_taken = (end_time - start_time)/1000;

    }

    return (
        <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col items-center justify-center p-4">
            <div className="h-screen flex flex-col mx-auto max-w-xl w-full px-4 bg-zinc-950 ">

                <div className="flex-1 w-full overflow-y-auto ">
                    <MessageList messages={messages} />
                    {aiResponse === true && <TypingIndicator/>}
                    {aiResponse === false && time_taken !== undefined && (
                        <p className="pl-2 text-zinc-400">Found in {time_taken}s</p>
                    )}
                </div>
                <MessageInput onSend={handleSend} />
            </div>
        </div>
    )
}