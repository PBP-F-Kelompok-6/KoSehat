# KoSehat: Sustainable Living Tracker for Campus Life

## Deskripsi Aplikasi

KoSehat adalah platform _web-based tracking_ & _scheduling_ gaya hidup berkelanjutan dan manajemen kebiasaan harian yang dirancang untuk membantu mahasiswa Universitas Indonesia dalam beradaptasi dengan kehidupan mandiri di kos atau asrama. Platform ini mendukung pembentukan kebiasaan harian yang seimbang (rutinitas olahraga ringan, jadwal tidur teratur, hidrasi, serta kesejahteraan fisik dan mental) di lingkungan baru. Selain itu, KoSehat memfasilitasi perencanaan pola makan sehat dan hemat guna menekan potensi limbah makanan dan mengurangi penggunaan kemasan sekali pakai dari makanan cepat saji.

## Pengguna Utama

Mahasiswa Universitas Indonesia yang tinggal di kos atau asrama dan ingin membentuk pola hidup sehat secara mandiri.

## Masalah yang Diselesaikan

1. Ketergantungan mahasiswa kos pada makanan cepat saji berwadah kemasan sekali pakai yang memicu penumpukan sampah di lingkungan hunian.
2. Kesulitan mahasiswa dalam menyesuaikan rutinitas harian yang seimbang, seperti pola tidur yang tidak teratur, minimnya aktivitas fisik, dan tingkat hidrasi yang terabaikan saat hidup mandiri.
3. Kurangnya perencanaan pola makan harian yang terstruktur, sehat, dan sesuai dengan anggaran mahasiswa.

## Peran Pengguna

- **Pengguna (Mahasiswa UI):** Mengelola profil pribadi, menyusun jadwal perencanaan makan sehat, mencatat aktivitas olahraga harian, memantau durasi tidur dan tingkat hidrasi, serta melihat statistik perkembangan kebiasaan harian.
- **Admin:** Mengelola katalog resep makanan sehat hemat, memperbarui daftar panduan olahraga ringan, serta menguraikan konten edukasi gaya hidup ramah lingkungan.

## Integrasi Public API

- **Spoonacular API / Edamam API:** Mengambil basis data resep masakan sehat beserta informasi nilai gizi.
- **ExerciseDB API:** Menyediakan katalog pilihan latihan fisik dan olahraga ringan tanpa alat yang dapat dilakukan di area kamar kos atau kampus.

## Daftar Modul & Pembagian Anggota Kelompok

| No  | Nama Modul                              | Deskripsi Modul                                                                                                                      | Penanggung Jawab                         |
| --- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------- |
| 1   | Autentikasi & Profil Pengguna           | Mengelola sistem masuk berbasis SSO UI, pendaftaran preferensi target kesehatan, dan pembaruan profil pengguna.                      | Zidane Ahdina Putra (2506583953)         |
| 2   | Meal Planner & Eco-Diet                 | Penjadwalan menu makan harian sehat hemat kos serta fitur pencatatan pengurangan konsumsi makanan cepat saji berwadah sekali pakai.  | Fata Akhmad Aulia (2506540853)           |
| 3   | Health & Habit Tracker                  | Pencatatan dan penjadwalan rutinitas harian yang seimbang meliputi olahraga ringan, durasi tidur teratur, dan asupan hidrasi harian. | Ranu Ario Sulistianto (2506657270)       |
| 4   | Dashboard & Impact Analytics            | Visualisasi statistik grafik kebiasaan hidup sehat harian dan estimasi dampak pengurangan sampah kemasan makanan.                    | Prajna Kausalya Damdami (2506657213)     |
| 5   | Katalog Resep & Edukasi Eco-Mindfulness | Pengelolaan katalog resep terintegrasi API luar serta fitur materi edukasi seputar kesejahteraan fisik dan mental mahasiswa kos.     | Dzakwan Farabi Al Muzhaffar (2506612436) |

## Figma

https://www.figma.com/design/hMQFcCGOQjJC8QqEYC8W7N/Untitled?node-id=0-1&p=f


## Module 4 — Dashboard & Impact Analytics

Module 4 uses Django MVT: `dashboard_analytics/views.py` prepares context, templates render the pages, and `dashboard_analytics/data.py` currently provides **sample/demo analytics**. The sample totals are not yet live data from Meal Planner or Habit Tracker.

### Local setup
1. Activate the project's virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Apply database migrations with `python manage.py migrate`.
4. Start Django with `python manage.py runserver`.

### Module 4 endpoints
- `/dashboard/` — Dashboard page.
- `/impact-analytics/` — Impact Analytics page; `?period=7d`, `30d`, `3m`, or `year` changes the displayed sample range.
- `/api/dashboard/` — JSON response for dashboard data.
- `/api/habits/` — POST JSON to store a habit entry in the temporary `HabitEntry` model.
- `/impact-analytics/report.csv?period=30d` — download a CSV report.

The temporary `HabitEntry` model is a bridge so the “Catat kebiasaan” form works before the Habit Tracker module is integrated. When the team's Habit Tracker model is ready, update `_dashboard_context()` in `dashboard_analytics/views.py` to query that model instead of `HabitEntry`; keep the template context keys stable to minimize frontend changes.

The Meal Planner cards, impact totals, and trend series are still sample data until Module 2's persisted model is available. Do not present these values as real personal analytics before integration.
