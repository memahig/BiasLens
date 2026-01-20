import extractor
import cross_examiner
import sys  # Added this for multi-line support

def run_bias_lens():
    print("\n" + "="*50)
    print("🛡️ BIASLENS v1.0: EPISTEMIC INTEGRITY SYSTEM")
    print("="*50)
    
    print("\nPaste your article below.")
    print("When finished, press ENTER then CTRL+D (on Mac) to start the audit:")
    print("-" * 30)
    
    # This reads everything until it sees the 'End of File' (Ctrl+D)
    text_to_scan = sys.stdin.read()

    if not text_to_scan.strip():
        print("❌ No text detected. Exiting.")
        return

    print("\n[Step 1] Fact/Opinion Extraction...")
    claims = extractor.extract_claims(text_to_scan)

    print("\n[Step 2] Integrity & Context Audit...")
    report = cross_examiner.cross_examine(claims)
    
    print("\n" + "#"*50)
    print("📢 FINAL BIASLENS INTELLIGENCE REPORT")
    print("#"*50)
    print(report)

if __name__ == "__main__":
    run_bias_lens()