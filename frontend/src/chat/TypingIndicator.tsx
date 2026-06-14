import { useEffect, useState } from "react"

export default function TypingIndicator() {
    const [dotCount, setDotCount] = useState<number>(1);

    useEffect(() => {
        const intervalId = setInterval(() => {
            setDotCount((prevCount) => {
                if (prevCount === 3) {
                    return 1;
                }
                return prevCount + 1
            });
        }, 500);

        return () => clearInterval(intervalId);
    }, []);

    return (
        <p className="pl-2 text-zinc-900">AI is thinking{'.'.repeat(dotCount)}</p>
    )
}