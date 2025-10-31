import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import os
import re
import unicodedata

DEFAULT_MAPPING = {
    "uif_ref": "A",
    "tradename": "B",
    "email": "C",
    "alt_email": "X",
    "tracer": "K",
    "status": "Q",
}

TEMPLATE_PATH = os.path.join(os.getcwd(), "company_list_template.xlsx")
OUTPUT_DIR = os.path.join(os.getcwd(), "output_lists")


def col_letter_to_index(letter: str) -> int:
    """Convert Excel column letter(s) to zero-based index. e.g. A->0, Z->25, AA->26"""
    letter = letter.strip().upper()
    if not re.fullmatch(r'[A-Z]+', letter):
        raise ValueError(f"Invalid column letter: '{letter}'")
    result = 0
    for ch in letter:
        result = result * 26 + (ord(ch) - ord('A') + 1)
    return result - 1


def sanitize_filename(name: str) -> str:
    """Make a safe filename from tracer name."""
    if name is None:
        name = "Unknown"
    # Normalize and remove characters not suitable for filenames
    name = unicodedata.normalize("NFKD", str(name))
    name = re.sub(r'[\\/:"*?<>|]+', "_", name)
    name = name.strip()
    if name == "":
        name = "Unknown"
    return name


class App:
    def __init__(self, root):
        self.root = root
        root.title("Phase Tracker -> Company Lists")
        root.geometry("820x560")

        # State
        self.input_path = None
        self.mapping = DEFAULT_MAPPING.copy()
        self.preview_df = None

        # UI layout
        frm_top = tk.Frame(root)
        frm_top.pack(fill="x", padx=10, pady=8)

        btn_select = tk.Button(frm_top, text="Select Phase Tracker Excel", command=self.select_file)
        btn_select.grid(row=0, column=0, sticky="w")

        self.lbl_file = tk.Label(frm_top, text="No file selected", anchor="w", fg="gray")
        self.lbl_file.grid(row=0, column=1, sticky="w", padx=8)

        # Mapping entries
        frm_map = tk.LabelFrame(root, text="Column Mapping (Excel letters) - change if file differs", padx=8, pady=8)
        frm_map.pack(fill="x", padx=10, pady=6)

        tk.Label(frm_map, text="UIF Reference (default A):").grid(row=0, column=0, sticky="e")
        self.ent_uif = tk.Entry(frm_map, width=6)
        self.ent_uif.insert(0, DEFAULT_MAPPING["uif_ref"])
        self.ent_uif.grid(row=0, column=1, padx=6)

        tk.Label(frm_map, text="Tradename (default B):").grid(row=0, column=2, sticky="e")
        self.ent_trade = tk.Entry(frm_map, width=6)
        self.ent_trade.insert(0, DEFAULT_MAPPING["tradename"])
        self.ent_trade.grid(row=0, column=3, padx=6)

        tk.Label(frm_map, text="Email (default C):").grid(row=0, column=4, sticky="e")
        self.ent_email = tk.Entry(frm_map, width=6)
        self.ent_email.insert(0, DEFAULT_MAPPING["email"])
        self.ent_email.grid(row=0, column=5, padx=6)

        tk.Label(frm_map, text="Alt Email (default X):").grid(row=1, column=0, sticky="e", pady=6)
        self.ent_alt = tk.Entry(frm_map, width=6)
        self.ent_alt.insert(0, DEFAULT_MAPPING["alt_email"])
        self.ent_alt.grid(row=1, column=1, padx=6, pady=6)

        tk.Label(frm_map, text="Tracer (default K):").grid(row=1, column=2, sticky="e", pady=6)
        self.ent_tracer = tk.Entry(frm_map, width=6)
        self.ent_tracer.insert(0, DEFAULT_MAPPING["tracer"])
        self.ent_tracer.grid(row=1, column=3, padx=6, pady=6)

        tk.Button(frm_map, text="Load Preview (first 3 rows)", command=self.load_preview).grid(row=1, column=5, padx=8)

        tk.Label(frm_map, text="Status (default Q):").grid(row=2, column=0, sticky="e", pady=6)
        self.ent_status = tk.Entry(frm_map, width=6)
        self.ent_status.insert(0, DEFAULT_MAPPING["status"])
        self.ent_status.grid(row=2, column=1, padx=6, pady=6)

        # Preview area
        frm_preview = tk.LabelFrame(root, text="Preview (first 3 rows) - used to check mapping", padx=8, pady=8)
        frm_preview.pack(fill="both", expand=True, padx=10, pady=6)

        self.txt_preview = tk.Text(frm_preview, height=12, wrap="none")
        self.txt_preview.pack(fill="both", expand=True)

        # Run button
        frm_run = tk.Frame(root)
        frm_run.pack(fill="x", padx=10, pady=6)
        tk.Button(frm_run, text="Generate Company Lists", bg="#2e8b57", fg="white", command=self.run_generate, width=24).pack(side="left")
        tk.Button(frm_run, text="Open output folder", command=self.open_output_folder).pack(side="left", padx=8)

        # Info
        frm_info = tk.Frame(root)
        frm_info.pack(fill="x", padx=10, pady=6)
        info_text = ("Notes:\n - The app reads the entire sheet when generating outputs but uses the first 3 rows for preview.\n"
                     " - Output files will be saved to ./output_lists/ named: {TracerName} - Company List.xlsx\n - Template headers (first row) from company_list_template.xlsx will be used for column order.\n")
        tk.Label(frm_info, text=info_text, justify="left", anchor="w").pack(fill="x")

    def select_file(self):
        path = filedialog.askopenfilename(title="Select Phase Tracker Excel file", filetypes=[("Excel files", "*.xlsx *.xls")])
        if path:
            self.input_path = path
            self.lbl_file.config(text=os.path.basename(path), fg="black")
            self.load_preview()

    def load_preview(self):
        if not self.input_path:
            messagebox.showinfo("Select file", "Please select the Phase tracker Excel file first.")
            return

        # Update mapping from entries
        self.mapping["uif_ref"] = self.ent_uif.get().strip() or DEFAULT_MAPPING["uif_ref"]
        self.mapping["tradename"] = self.ent_trade.get().strip() or DEFAULT_MAPPING["tradename"]
        self.mapping["email"] = self.ent_email.get().strip() or DEFAULT_MAPPING["email"]
        self.mapping["alt_email"] = self.ent_alt.get().strip() or DEFAULT_MAPPING["alt_email"]
        self.mapping["tracer"] = self.ent_tracer.get().strip() or DEFAULT_MAPPING["tracer"]
        self.mapping["status"] = self.ent_status.get().strip() or DEFAULT_MAPPING["status"]

        try:
            # Read first 3 rows without header inference
            preview = pd.read_excel(self.input_path, header=None, nrows=3, engine="openpyxl")
        except Exception as e:
            messagebox.showerror("Error reading file", f"Could not read Excel file:\n{e}")
            return

        self.preview_df = preview
        # Show preview with column letters as Excel style (A, B, C...)
        col_headers = []
        for i in range(preview.shape[1]):
            # convert index to letter(s)
            n = i + 1
            s = ""
            while n > 0:
                n, rem = divmod(n-1, 26)
                s = chr(rem + ord('A')) + s
            col_headers.append(s)
        # build display
        display_lines = []
        header_line = " | ".join([f"{col_headers[i]}" for i in range(len(col_headers))])
        display_lines.append(header_line)
        display_lines.append("-" * max(50, len(header_line)))
        for ridx in range(preview.shape[0]):
            row = preview.iloc[ridx].fillna("").astype(str).tolist()
            display_lines.append(" | ".join(row))
        display_text = "\n".join(display_lines)
        self.txt_preview.delete("1.0", tk.END)
        self.txt_preview.insert(tk.END, display_text)

        messagebox.showinfo("Preview loaded", "Preview (first 3 rows) loaded. Verify mappings and then click Generate.")

    def run_generate(self):
        if not self.input_path:
            messagebox.showinfo("Select file", "Please select the Phase tracker Excel file first.")
            return

        # update mapping
        try:
            mapping = {k: col_letter_to_index(v) for k, v in {
                "uif_ref": self.ent_uif.get().strip() or DEFAULT_MAPPING["uif_ref"],
                "tradename": self.ent_trade.get().strip() or DEFAULT_MAPPING["tradename"],
                "email": self.ent_email.get().strip() or DEFAULT_MAPPING["email"],
                "alt_email": self.ent_alt.get().strip() or DEFAULT_MAPPING["alt_email"],
                "tracer": self.ent_tracer.get().strip() or DEFAULT_MAPPING["tracer"],
                "status": self.ent_status.get().strip() or DEFAULT_MAPPING["status"],
            }.items()}
        except Exception as e:
            messagebox.showerror("Invalid mapping", f"Error with column letters: {e}")
            return

        # Read full sheet (no header inference)
        try:
            df = pd.read_excel(self.input_path, header=None, engine="openpyxl")
        except Exception as e:
            messagebox.showerror("Error reading file", f"Could not read Excel file:\n{e}")
            return

        # Ensure requested columns exist
        needed_idxs = [mapping["uif_ref"], mapping["tradename"], mapping["email"], mapping["alt_email"], mapping["tracer"], mapping["status"]]
        max_idx = max(needed_idxs)
        if max_idx >= df.shape[1]:
            messagebox.showerror("Column out of range", f"One of the mapped columns ({max_idx}) is outside the sheet's column count ({df.shape[1]}). Check your mappings.")
            return

        pattern = re.compile(r'^\s*not\s*[_ -]?\s*started\s*$', re.IGNORECASE)
        mask = df.iloc[:, mapping["status"]].astype(str).str.fullmatch(pattern).fillna(False)
        df = df[mask].reset_index(drop=True)

        # Extract columns: create normalized dataframe with headers we will use
        alt_col = df.iloc[:, mapping["alt_email"]]
        alt_clean = alt_col.where(pd.notna(alt_col), "").astype(str)
        out_df = pd.DataFrame({
            "UIF Reference Number": df.iloc[:, mapping["uif_ref"]].astype(str).fillna(""),
            "Tradename": df.iloc[:, mapping["tradename"]].astype(str).fillna(""),
            "Email Address": df.iloc[:, mapping["email"]].astype(str).fillna(""),
            "Alternative Email": alt_clean,
            "Tracer": df.iloc[:, mapping["tracer"]].astype(str).fillna(""),
        })

        # Load template headers if exists, else default order
        if os.path.exists(TEMPLATE_PATH):
            try:
                tpl = pd.read_excel(TEMPLATE_PATH, header=None, nrows=1, engine="openpyxl")
                # Flatten first row for headers
                template_headers = tpl.iloc[0].fillna("").astype(str).tolist()
                # Determine which of our columns map to template headers; if template doesn't include them, we'll append
                # We'll create output columns in the order of template_headers but only include columns we have
                cols_we_have = ["UIF Reference Number", "Tradename", "Email Address", "Alternative Email"]
                ordered_cols = []
                for h in template_headers:
                    if h.strip() in cols_we_have:
                        ordered_cols.append(h.strip())
                # append any that weren't in template first row
                for c in cols_we_have:
                    if c not in ordered_cols:
                        ordered_cols.append(c)
                final_order = ordered_cols
            except Exception:
                final_order = ["UIF Reference Number", "Tradename", "Email Address", "Alternative Email"]
        else:
            final_order = ["UIF Reference Number", "Tradename", "Email Address", "Alternative Email"]

        # Group by tracer and write files
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        grouped = out_df.groupby("Tracer", dropna=False)
        written_files = []
        for tracer, group in grouped:
            # remove empty tracer (use 'Unknown' label)
            tracer_name = tracer if (isinstance(tracer, str) and tracer.strip() != "") else "Unknown"
            tracer_clean = sanitize_filename(tracer_name)
            out_path = os.path.join(OUTPUT_DIR, f"{tracer_clean} - Company List.xlsx")

            # Build output dataframe in final_order
            save_df = group.copy()
            save_df = save_df.rename(columns={
                "UIF Reference Number": "UIF Reference Number",
                "Tradename": "Tradename",
                "Email Address": "Email Address",
                "Alternative Email": "Alternative Email",
            })
            # Reindex to final_order (if some header names differ, safe default)
            save_df = save_df[[c for c in final_order if c in save_df.columns]]

            # drop the 'Tracer' column if present
            if "Tracer" in save_df.columns:
                save_df = save_df.drop(columns=["Tracer"], errors="ignore")

            # Write to Excel (data only)
            try:
                with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
                    save_df.to_excel(writer, index=False, sheet_name="Companies")
                written_files.append(out_path)
            except Exception as e:
                messagebox.showerror("Write error", f"Could not write file {out_path}:\n{e}")
                return

        messagebox.showinfo("Done", f"Generated {len(written_files)} files in {OUTPUT_DIR}")
        # Optionally open the folder
        self.open_output_folder()

    def open_output_folder(self):
        if not os.path.exists(OUTPUT_DIR):
            messagebox.showinfo("No output", "Output folder does not exist yet. Generate files first.")
            return
        # Open file explorer at output folder
        try:
            if os.name == "nt":
                os.startfile(OUTPUT_DIR)
            elif os.name == "posix":
                # mac or linux
                try:
                    os.system(f'xdg-open "{OUTPUT_DIR}"')
                except Exception:
                    os.system(f'open "{OUTPUT_DIR}"')
            else:
                messagebox.showinfo("Output folder", OUTPUT_DIR)
        except Exception:
            messagebox.showinfo("Output folder", OUTPUT_DIR)


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
