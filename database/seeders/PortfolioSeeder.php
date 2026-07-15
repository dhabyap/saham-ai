<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\Project;

class PortfolioSeeder extends Seeder
{
    public function run()
    {
        $projects = [
            [
                'title' => 'Analisa Saham IDX',
                'slug' => 'analisa-saham-idx',
                'type' => 'Full-Stack Analysis',
                'category' => 'professional',
                'thumbnail' => '/images/projects/analisa-saham.jpg',
                'tags' => ['FastAPI', 'Vue 3', 'MySQL', 'Telegram Bot'],
                'status' => 'published',
                'order' => 1,
                'description' => 'Platform analisis saham IDX, AI scoring, shareholder monitoring, dan real-time Telegram alerts.'
            ],
            [
                'title' => 'Kairos Whale Tracker',
                'slug' => 'kairos-tracker',
                'type' => 'Data Monitoring',
                'category' => 'professional',
                'thumbnail' => '/images/projects/kairos.jpg',
                'tags' => ['FastAPI', 'Vue 3', 'Neumorphism'],
                'status' => 'published',
                'order' => 2,
                'description' => 'Whale tracker dan sistem monitor cron job dengan visualisasi Neumorphism.'
            ],
            [
                'title' => 'Binance Alpha Tracker',
                'slug' => 'alpha-tracker',
                'type' => 'Crypto Analytics',
                'category' => 'personal',
                'thumbnail' => '/images/projects/alpha-tracker.jpg',
                'tags' => ['FastAPI', 'BSC', 'AI Advisor', 'Telegram Bot'],
                'status' => 'published',
                'order' => 3,
                'description' => 'Sistem deteksi dini koin BSC pre-trending dengan analisis AI dan scoring otomatis.'
            ],
            [
                'title' => 'GrowthRing',
                'slug' => 'growthring',
                'type' => 'Web App',
                'category' => 'personal',
                'thumbnail' => '/images/projects/growthring.jpg',
                'tags' => ['Next.js', 'Prisma', 'MariaDB', 'Framer Motion'],
                'status' => 'published',
                'order' => 4,
                'description' => 'Platform pelacak aktivitas komunitas di X dengan stack modern.'
            ]
        ];

        foreach ($projects as $p) {
            Project::updateOrCreate(['slug' => $p['slug']], $p);
        }
    }
}
