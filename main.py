# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
if __name__=='__main__':
    import sys
    if '--ui-review' in sys.argv:
        import os
        import traceback
        from pathlib import Path
        os.environ['QT_QPA_PLATFORM']='windows' if '--native-ui' in sys.argv else 'offscreen'
        output=Path(sys.argv[sys.argv.index('--ui-review')+1])
        output.mkdir(parents=True,exist_ok=True)
        try:
            from cyber.ui_review import run
            run(output,all_tools=True)
        except Exception:
            (output/'error.txt').write_text(traceback.format_exc(),encoding='utf-8')
            raise SystemExit(1)
    elif '--smoke-test' in sys.argv:
        import os
        import traceback
        from pathlib import Path
        os.environ['QT_QPA_PLATFORM']='offscreen'
        output=Path(sys.argv[sys.argv.index('--smoke-test')+1])
        output.mkdir(parents=True,exist_ok=True)
        try:
            from cyber.smoke import run
            run(output)
        except Exception:
            (output/'error.txt').write_text(traceback.format_exc(),encoding='utf-8')
            raise SystemExit(1)
    else:
        from cyber.ui import main
        raise SystemExit(main())
