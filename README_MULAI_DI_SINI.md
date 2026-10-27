# Model 3D Pelipat Pakaian Aksesibel - Rev B

**Tanggal:** 28 Oktober 2026. **Satuan:** milimeter. **Tahap:** prototipe mekanik untuk percobaan, bukan desain produksi yang sudah diuji fisik.

## Mulai dari sini

1. Buka **COBA_MEKANISME.html** dengan Chrome atau Edge. Tidak perlu internet. Putar kamera dengan mouse dan gerakkan slider kiri, kanan, serta bawah. Tombol demo menjalankan lipat-lalu-buka satu panel pada satu waktu.
2. Untuk CAD, buka **step/assembly_open.step**. Komponen diberi nama dan dipisahkan sebagai solid. STEP ini tidak menyimpan joint atau solver gerak; gunakan sumbu pada **source/joint_axes.json** bila memasang joint di perangkat lunak CAD lain.
3. Alternatif mesh rakitan tersedia di **obj/assembly_open.obj**. Simpan **assembly_open.mtl** di folder yang sama agar warna terbaca. OBJ tidak membawa informasi joint.
4. **Cetak kupon di folder tests terlebih dahulu**, bersama satu pasang hinge_A dan hinge_B serta satu splice_strap. Jangan langsung mencetak semua panel.
5. Setelah toleransi cocok, impor STL atau 3MF per bagian ke Anycubic Slicer Next. Pilih profil Kobra X dan bahan Anda sendiri.

3MF yang diberikan adalah **model geometri standar**, masing-masing satu bagian dengan unit mm dan orientasi cetak. Ini bukan proyek slicer dengan temperatur, support, atau kecepatan yang sudah dikunci. Tidak ada G-code dalam paket.

## Bentuk mekanik yang dimodelkan

- Envelope papan sekitar **630 x 540 mm**, di luar penanda kerah dan pod kontrol.
- Celah mekanik dialokasikan **di dalam** envelope tersebut: sayap selebar 206 mm, bagian tengah 202 mm, celah antarpanel 8 mm.
- Dua sayap penuh, satu panel acuan tengah atas, satu flap tengah bawah.
- Total **12 ubin panel cetak**, dirakit menjadi empat bidang. Sambungan ubin bersifat kaku.
- Tebal pelat 4 mm, rib bawah 4 mm, permukaan atas pada Z=8 mm.
- Tiga sumbu lipat: X=210, X=420, dan Y=270; ketinggian sumbu Z=15 mm.
- Enam unit engsel baut: dua per sumbu. Tiap unit menggunakan satu daun A, satu daun B, dan pin logam sekitar diameter 4 mm.
- Penanda kerah, tiga penanda indeks rendah, pegangan jari, pod terpisah, tiga overlay tombol taktil, dan label Braille terpisah.

Gerak yang dimaksud adalah **lipat satu panel, buka kembali, lalu pindah ke panel berikutnya**. Menutup ketiganya bersamaan bukan alur operasi dan dapat menghasilkan tumpang tindih di pratinjau. Pratinjau menampilkan kinematika benda kaku; tidak menyimulasikan kain, gaya tangan, kelenturan, atau kekuatan engsel.

## Isi folder

| Folder/berkas | Isi |
| --- | --- |
| step/assembly_open.step | Rakitan terbuka dengan solid terpisah |
| step/pose_left_90.step | Contoh pose kiri 90 derajat |
| step/pose_right_90.step | Contoh pose kanan 90 derajat |
| step/pose_bottom_90.step | Contoh pose bawah 90 derajat |
| step/*.step lainnya | Solid per bagian, dalam koordinat desain |
| obj/ | Mesh rakitan terbuka dan material |
| stl/ | Bagian cetak utama dan adaptor sensor opsional |
| tests/ | Lima geometri kupon uji |
| 3mf/ | Padanan model 3MF untuk setiap bagian utama, opsional, dan kupon |
| parts_manifest.csv / .json | Nama, jumlah cetak, kategori, dimensi, volume, dan catatan |
| collision_report.json | Hasil sampling benturan benda kaku |
| validation_summary.json | Ringkasan pemeriksaan pembuat model |
| independent_validation.json | Pemeriksaan ekspor oleh pembaca format terpisah |
| source/ | Sumber parametrik, sumbu joint, dan data pratinjau |

Orientasi STEP mengikuti koordinat desain, sedangkan STL/3MF sudah diputar dan diturunkan ke Z=0 untuk cetak. Perbedaan posisi antarformat ini disengaja.

## Jumlah cetak bagian utama

| Nama bagian | Jumlah |
| --- | ---: |
| panel_L1 sampai panel_L4 | Masing-masing 1 |
| panel_R1 sampai panel_R4 | Masing-masing 1 |
| panel_F1 dan panel_F2 | Masing-masing 1 |
| panel_B1 dan panel_B2 | Masing-masing 1 |
| splice_strap | 16 |
| hinge_A | 6 |
| hinge_B | 6 |
| marker_collar | 1 |
| marker_index | 3 |
| control_base dan control_lid | Masing-masing 1 |
| braille_kembali, braille_mulai, braille_ulang | Masing-masing 1 |
| button_overlay_back, button_overlay_next, button_overlay_repeat | Masing-masing 1 |

Bagian dengan awalan **TEST_** adalah kupon, bukan komponen tambahan pada rakitan. **OPTION_sensor_adapter_template** hanya template opsional dan tidak digunakan dalam rakitan. Pin, tombol listrik, dan knop yang terlihat sebagai referensi pada rakitan **tidak termasuk bagian untuk dicetak**.

Peta penempatan ubin dari tampak atas konseptual; penanda kerah berada di atas dan pod kontrol di bawah:

```text
             PENANDA KERAH
        L1  |  F1  |  R1
        L2  |  F2  |  R2
        L3  |  B1  |  R3
        L4  |  B2  |  R4
              POD KONTROL
```

F1-F2 disambung kaku. B1-B2 juga disambung kaku, tetapi F2 dan B1 dipisahkan oleh sumbu engsel bawah. Beri nama bagian pada sisi bawah dengan penanda setelah dicetak agar urutannya tidak tertukar.

## Kupon dan urutan percobaan

### A. Lubang pin

Cetak TEST_pin_bores_42_43_44_45. Empat lubang berturut-turut sepanjang sisi panjang adalah diameter **4,2 / 4,3 / 4,4 / 4,5 mm**. Cocokkan dengan pin 4 mm yang benar-benar akan digunakan.

Model engsel utama memakai bore **4,4 mm** dan celah aksial sekitar 0,6 mm. Jika hasil cetak memerlukan ukuran berbeda, ubah parameter sumber dan ekspor ulang. Jangan memaksa pin dengan menekuk daun engsel.

### B. Satu unit engsel

Cetak hinge_A, hinge_B, TEST_hinge_panel_fixed, dan TEST_hinge_panel_moving. Gabungkan dengan pin dan empat baut M3. Putar perlahan dari terbuka sampai terlipat dan kembali.

Periksa putaran ringan, kelonggaran pin, sisa support di bore/knuckle, ruang panel, serta posisi jari. Pengujian ini belum memakai kain; ulangi dengan beberapa lapis kain sasaran.

### C. Sambungan ubin

Cetak TEST_splice_panel_A, TEST_splice_panel_B, dan satu splice_strap. Dua tepi kupon dirapatkan; lubang berada 18 mm dari seam. Gunakan dua baut countersunk M3 dan dua mur M3. Kupon ini memeriksa strap, mur, dan kepala rata. Jangan menambahkan spacer seam tanpa menyesuaikan posisi lubang kupon.

Pada panel utama, celah seam 0,4 mm sudah diperhitungkan terhadap posisi baut. Dua strap dipakai pada setiap seam.

## Pengikat dan komponen yang dibeli

| Kebutuhan | Jumlah awal | Keterangan |
| --- | ---: | --- |
| Pin/baut sumbu diameter sekitar 4 mm | 6 | Panjang referensi batang 40 mm; panjang akhir mengikuti kepala, mur/retainer dan washer yang dipilih |
| Baut countersunk M3 x 8 + mur M3 | 32 pasang | Sambungan 16 strap; M3x10 akan menonjol di bawah bidang meja pada tumpukan ini |
| Baut countersunk M3 x 10 + mur M3 | 24 pasang | Dua baut per daun engsel |
| Baut countersunk M3 untuk penanda kerah | 2 pasang | Kandidat M3x10; periksa panjang dan kaki antiselip |
| Sekrup penutup casing | 4 | Lubang lid 3,4 mm; pilot base 2,7 mm untuk ditap atau screw pembentuk ulir yang sesuai |
| Push button panel-mount diameter 16 mm | 3 | Lubang panel 16,3 mm; kepala tombol perlu bidang rata diameter minimal 16 mm untuk overlay |
| Pot volume panel-mount | 1 | Lubang dudukan nominal 7,3 mm; ukuran shaft/ulir dan knop perlu dicocokkan |
| Speaker, grommet kabel, kabel, tie, perekat label | Sesuai modul | Belum ditentukan berdasarkan pengukuran komponen nyata |
| Kaki antiselip tipis | Sesuai bidang tumpu | Pasang merata, tanpa menutup akses mur atau mengganggu engsel |

Gunakan penahan pin agar sumbu tidak bergeser keluar. Kepala baut/retainer pin belum dirinci pada model referensi; cek ruang dengan panel bergerak. Jangan mengencangkan mur sampai engsel terjepit atau plastik rusak.

Di sisi kiri dan bawah, daun **A** dipasang pada bagian tetap dan **B** pada panel bergerak. Di sisi kanan, perannya dibalik: **B tetap dan A bergerak**. Tidak perlu mencerminkan STL di slicer. Posisi tepat terlihat pada STEP rakitan.

## Pengaturan cetak awal untuk dicoba

| Bagian | Orientasi yang diekspor | Titik awal pengaturan |
| --- | --- | --- |
| Panel | Permukaan kain menghadap bed, rib menghadap atas | Layer 0,20 mm; 4 perimeter; infill awal 15-25%; verifikasi kekakuan |
| Strap | Sisi atas rata ke bed, kantong mur menghadap atas | 5-6 perimeter atau infill padat; uji torsi baut |
| Engsel A/B | Sumbu bore vertikal | **Support dan brim diperlukan** pada ledge knuckle; bersihkan dan ukur bore sebelum dirakit |
| Label Braille | Dasar rata di bed, titik ke atas | Layer 0,12-0,16 mm; periksa titik dan uji pembaca Braille |
| Casing/lid | Posisi dasar rata sebagaimana ekspor | Periksa orientasi dan jangkauan brim di slicer |
| Overlay tombol dan penanda | Dasar rata di bed | Perekat sesuai bahan; tekstur diuji dengan pengguna |

PLA dapat dipakai untuk percobaan ukuran. PETG adalah kandidat untuk engsel/strap, tetapi sifat dan toleransi cetaknya harus diuji. Nilai pengaturan di atas merupakan titik awal, bukan profil yang sudah dibuktikan pada printer Anda.

Bagian terlebar adalah casing 250 mm. Pada bed 260 mm, jangan menambahkan brim besar; brim 4 mm per sisi menghasilkan sekitar 258 mm, sedangkan brim 6 mm per sisi melewati bed. Periksa area purge dan batas efektif profil printer.

## Braille

Label memakai huruf Latin enam titik tanpa kontraksi: **kembali**, **mulai**, dan **ulang**. Diameter titik nominal 1,5 mm, tinggi 0,75 mm, pitch di dalam sel 2,4 mm, pitch sel 6,2 mm.

Susunan tersebut merupakan model huruf yang dapat diperiksa, bukan jaminan keterbacaan akhir. Minta pembaca Braille bahasa Indonesia memvalidasi label cetak sebelum dipasang permanen. Jangan skala label bersamaan dengan casing.

## Batas yang masih memerlukan pengukuran fisik

- **Dudukan AS5600 dan penggerak magnet belum final.** Adaptor opsional adalah template slot generik, bukan dudukan yang sudah muat pada tiga sendi. Magnet harus mengikuti knuckle/panel bergerak, bukan pin yang bebas atau diam.
- Pod memakai ruang dan lubang generik. PCB, dudukan speaker, lubang saklar daya, grommet, ulir pot, dan kedalaman tombol perlu disesuaikan dengan komponen yang dibeli. Base menyediakan slot pengikat, tanpa mengklaim pola baut PCB tertentu.
- Kepala tombol/knop pada rakitan adalah volume referensi. Overlay taktil berupa penanda tempel, bukan mekanisme push button listrik.
- Tidak ada pemodelan kain, pengujian kekuatan, simulasi keausan, atau validasi jepitan jari dengan pengguna.

## Bahan dan hasil pemeriksaan

Model menghitung volume benda padat untuk setiap bagian. Total ekuivalen PLA padat semua bagian cetak terpasang berada di sekitar **2,03 kg**, di luar hardware logam, elektronik, kupon, support, dan purge. Angka ini lebih tinggi daripada perkiraan awal konsep karena penguat bawah, sambungan, dan engsel sekarang sudah dimodelkan.

Konsumsi slicer dapat lebih rendah dengan infill, tetapi support dan percobaan menambah kebutuhan. Untuk perencanaan awal satu set penuh, sediakan sekitar **3 kg** sebelum menilai konsumsi dari slicer. Ini bukan estimasi harga produksi.

Seluruh solid dan mesh diperiksa saat ekspor. Laporan independen membaca ulang STL, 3MF, dan STEP. Pemeriksaan benturan mengambil sampel sudut 0-180 setiap 15 derajat pada satu panel bergerak, dengan panel lain terbuka. Hasil pada file laporan berlaku untuk sampling tersebut; bukan pembuktian bebas bentur kontinu atau pengujian kain.

Lihat validation_summary.json, independent_validation.json, dan collision_report.json untuk angka aktual pada paket ini.
