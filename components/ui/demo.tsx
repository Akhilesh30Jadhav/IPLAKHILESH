// file: demo.tsx
import { LinkCard } from '@/components/ui/card-26'; // Adjust the import path as needed

// Data for the cards to demonstrate reusability
const cardData = [
    {
        title: 'LinkedIn',
        description: "I am not posting that often on LinkedIn, but hey, let's connect.",
        imageUrl: 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=640&q=80',
        href: 'https://www.linkedin.com/',
    },
    {
        title: 'Instagram',
        description: 'No design stuff here. Everyday life, hobbies and my daughter Marta.',
        imageUrl: 'https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&w=640&q=80',
        href: 'https://www.instagram.com/',
    },
    {
        title: 'Pudding Studio',
        description: 'Check Puddings website. You will find some designs there too.',
        imageUrl: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=640&q=80',
        href: 'https://pudding.cool/',
    },
];

export default function LinkCardDemo() {
    return (
        <div className="flex h-full w-full items-center justify-center bg-background p-4 md:p-8">
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {cardData.map((card) => (
                    <LinkCard
                        key={card.title}
                        title={card.title}
                        description={card.description}
                        imageUrl={card.imageUrl}
                        href={card.href}
                    />
                ))}
            </div>
        </div>
    );
}
