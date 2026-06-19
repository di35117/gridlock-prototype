import { redirect } from 'next/navigation';

export default function Home() {
  // Automatically send users to the dashboard when they load localhost:3000
  redirect('/dashboard');
}