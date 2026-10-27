# Menghasilkan ulang model

Sumber memakai CadQuery/OCP untuk BREP dan STEP, serta trimesh untuk mesh.
Gunakan Python 3.12 64-bit. Tidak ada runtime CAD yang dibundel dalam ZIP.

Di folder source, pasang dependensi ke folder lokal:

    python -m pip install --target .cad_runtime -r requirements.txt
    python cad/build_model.py

Hasil baru muncul di source/output/cad_rev_b. Salin panduan utama secara terpisah
bila ingin mendistribusikan paket hasil rebuild. Koneksi internet hanya diperlukan
untuk memasang dependensi; pratinjau HTML yang sudah jadi bekerja offline.

STEP berisi solid dan nama bagian, bukan riwayat feature tree atau joint solver.
Parameter dan susunan geometrinya dapat diedit di cad/build_model.py. Perubahan
dimensi perlu diikuti pengujian ulang format, benturan, serta kupon cetak.

Validator tambahan memakai lib3mf dan pembaca STEP. Jalur interpreter untuk
bagian pengujian independen mungkin perlu disesuaikan dengan komputer Anda.
