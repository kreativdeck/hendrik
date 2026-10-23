"""Tests für ftps_deploy.py. Kein Netzwerk, keine echten Zugangsdaten."""
from __future__ import annotations

import contextlib
import ftplib
import io
import os
import posixpath
import ssl
import tempfile
import unittest
from unittest import mock

import ftps_deploy as fd

ROOT = fd.ALLOWED_REMOTE_DIR
SITE = "https://" + fd.ALLOWED_SITE_HOST
PASSWORD = "s3cr3t-PW-Zeichenfolge"

ENV = {
    "FTP_HOST": "ftp.example.test",
    "FTP_PORT": "21",
    "FTP_USER": "deploy-user",
    "FTP_PASSWORD": PASSWORD,
    "FTP_REMOTE_DIR": ROOT,
    "SITE_URL": SITE,
    "DEPLOY_ENABLED": "true",
}


def write(base: str, rel: str, data: bytes = b"x") -> None:
    path = os.path.join(base, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)


def make_build(base: str) -> None:
    write(base, "index.html", b"<!doctype html><html><body>home</body></html>")
    write(base, ".htaccess", b"RewriteEngine On\n")
    write(base, "404.html", b"<html>404</html>")
    write(base, "about/index.html", b"<html>about</html>")
    write(base, "robots.txt", f"User-agent: *\nSitemap: {SITE}/sitemap.xml\n".encode())
    write(base, "sitemap.xml", b"<urlset/>")
    write(base, "_astro/app.abc.css", b"body{}")
    write(base, "_astro/app.abc.js", b"console.log(1)")
    write(base, "assets/images/Two Stripes/pic one.jpg", b"jpgdata")
    write(base, "api/contact.php", b"<?php // x")


class FakeRemote:
    """In-Memory-Server mit Operationsprotokoll."""

    READ = {"resolve_dir", "list_dir", "size"}

    def __init__(self, root=ROOT, rename_overwrite=True, fail_store_for=None):
        self.root = root
        self.dirs = {root}
        self.files = {}
        self.ops = []
        self.rename_overwrite = rename_overwrite
        self.fail_store_for = fail_store_for
        self.closed = False

    def connect(self):
        self.ops.append(("connect",))

    def close(self):
        self.closed = True

    def resolve_dir(self, path):
        self.ops.append(("resolve_dir", path))
        return path if path in self.dirs else None

    def list_dir(self, path):
        self.ops.append(("list_dir", path))
        if path not in self.dirs:
            return None
        out = {}
        for d in self.dirs:
            if posixpath.dirname(d) == path and d != path:
                out[posixpath.basename(d)] = fd.RemoteEntry("dir", None)
        for f, data in self.files.items():
            if posixpath.dirname(f) == path:
                out[posixpath.basename(f)] = fd.RemoteEntry("file", len(data))
        return out

    def size(self, path):
        self.ops.append(("size", path))
        return len(self.files[path]) if path in self.files else None

    def mkdir(self, path):
        self.ops.append(("mkdir", path))
        assert posixpath.dirname(path) in self.dirs
        self.dirs.add(path)

    def store(self, path, fp):
        self.ops.append(("store", path))
        data = fp.read()
        if self.fail_store_for and self.fail_store_for in path:
            raise ftplib.error_temp("426 Übertragung abgebrochen")
        self.files[path] = data

    def rename(self, src, dst):
        self.ops.append(("rename", src, dst))
        if dst in self.files and not self.rename_overwrite:
            raise ftplib.error_perm("550 Datei existiert")
        self.files[dst] = self.files.pop(src)

    def delete(self, path):
        self.ops.append(("delete", path))
        if path not in self.files:
            raise ftplib.error_perm("550 nicht vorhanden")
        del self.files[path]

    def writes(self):
        return [op for op in self.ops if op[0] not in self.READ and op[0] != "connect"]


class FakeWeb:
    """Liefert Dateien aus einem FakeRemote-Ordner, wie ein korrekt zugeordneter Webroot."""

    def __init__(self, remote, docroot=ROOT, htaccess_status=403, not_found_status=404):
        self.remote = remote
        self.docroot = docroot
        self.htaccess_status = htaccess_status
        self.not_found_status = not_found_status
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        assert url.startswith(SITE)
        path = url[len(SITE):].split("?")[0]
        if path == "/.htaccess":
            return fd.HttpResponse(self.htaccess_status, "text/html", b"")
        key = self.docroot + ("/index.html" if path == "/" else path)
        key = key.replace("%20", " ")
        data = self.remote.files.get(key)
        if data is None:
            return fd.HttpResponse(self.not_found_status, "text/html", b"nf")
        ctype = "text/html" if key.endswith(".html") else "application/octet-stream"
        return fd.HttpResponse(200, ctype, data)


class TempBuildCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.build = os.path.join(self._tmp.name, "dist")
        os.makedirs(self.build)
        make_build(self.build)

    def run_main(self, args, env=None, remote=None, web=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = fd.main(
                args,
                dict(ENV if env is None else env),
                remote_factory=(lambda cfg: remote) if remote is not None else None,
                http=web,
                sleep=lambda s: None,
            )
        return code, out.getvalue(), err.getvalue()


class ConfigTests(unittest.TestCase):
    def test_valid(self):
        cfg = fd.load_config(ENV)
        self.assertEqual((cfg.port, cfg.remote_dir, cfg.site_url), (21, ROOT, SITE))
        self.assertNotIn(PASSWORD, repr(cfg))

    def test_missing_values_named_without_secrets(self):
        env = {k: v for k, v in ENV.items() if k not in ("FTP_HOST", "FTP_PASSWORD")}
        with self.assertRaises(fd.ConfigError) as ctx:
            fd.load_config(env)
        self.assertIn("FTP_HOST", str(ctx.exception))
        self.assertIn("FTP_PASSWORD", str(ctx.exception))

    def test_port_default(self):
        env = dict(ENV, FTP_PORT="")
        self.assertEqual(fd.load_config(env).port, 21)

    def test_invalid_port(self):
        for bad in ("0", "abc", "70000"):
            with self.assertRaises(fd.ConfigError):
                fd.load_config(dict(ENV, FTP_PORT=bad))

    def test_remote_dir_exact_only(self):
        self.assertEqual(fd.load_config(dict(ENV, FTP_REMOTE_DIR=ROOT + "/")).remote_dir, ROOT)
        for bad in ("/", "", "/other.example.org", ROOT + "/sub", ROOT + "/../x", "/jmc", "hendrik.kreativdeck.dev", "/hendrik.kreativdeck.dev2"):
            with self.assertRaises(fd.ConfigError, msg=bad):
                fd.load_config(dict(ENV, FTP_REMOTE_DIR=bad))

    def test_site_url_exact_host(self):
        for bad in ("http://hendrik.kreativdeck.dev", "https://www.deinedomain.de", "https://hendrik.kreativdeck.dev/sub",
                    "https://user@hendrik.kreativdeck.dev", "https://hendrik.kreativdeck.dev:8443",
                    "https://evil.example/hendrik.kreativdeck.dev", "https://hendrik.kreativdeck.dev?x=1"):
            with self.assertRaises(fd.ConfigError, msg=bad):
                fd.load_config(dict(ENV, SITE_URL=bad))
        self.assertEqual(fd.load_config(dict(ENV, SITE_URL=SITE + "/")).site_url, SITE)

    def test_host_must_be_plain_hostname(self):
        for bad in ("ftps://host", "host/path", "user@host", "host:21", "ho st"):
            with self.assertRaises(fd.ConfigError, msg=bad):
                fd.load_config(dict(ENV, FTP_HOST=bad))


class ScanTests(TempBuildCase):
    def test_valid_build(self):
        files = fd.scan_build(self.build)
        rels = [f.rel for f in files]
        self.assertIn(".htaccess", rels)
        self.assertIn("assets/images/Two Stripes/pic one.jpg", rels)

    def assertBad(self, fragment):
        with self.assertRaises(fd.BuildError) as ctx:
            fd.scan_build(self.build)
        self.assertIn(fragment, str(ctx.exception))

    def test_missing_htaccess(self):
        os.remove(os.path.join(self.build, ".htaccess"))
        self.assertBad(".htaccess: fehlt")

    def test_missing_index(self):
        os.remove(os.path.join(self.build, "index.html"))
        self.assertBad("index.html: fehlt")

    def test_forbidden_names(self):
        for rel in (".env", ".env.local", ".git/config", ".DS_Store", "assets/._pic.jpg", "node_modules/x.js",
                    ".kd-tmp-abc", "kd-deploy-probe-1.txt", "sub/.gitignore"):
            with self.subTest(rel=rel):
                with tempfile.TemporaryDirectory() as fresh:
                    make_build(fresh)
                    write(fresh, rel)
                    with self.assertRaises(fd.BuildError):
                        fd.scan_build(fresh)

    def test_gitkeep_is_allowed(self):
        write(self.build, "assets/images/.gitkeep", b"")
        self.assertIn("assets/images/.gitkeep", [f.rel for f in fd.scan_build(self.build)])

    def test_symlink_rejected(self):
        os.symlink("/etc/hosts", os.path.join(self.build, "link.txt"))
        self.assertBad("link.txt: Symlink")

    def test_symlinked_dir_rejected(self):
        os.symlink(self._tmp.name, os.path.join(self.build, "linkdir"))
        self.assertBad("linkdir: Symlink")

    def test_source_symlink_rejected(self):
        link = os.path.join(self._tmp.name, "dist-link")
        os.symlink(self.build, link)
        with self.assertRaises(fd.BuildError):
            fd.scan_build(link)

    def test_control_characters_rejected(self):
        write(self.build, "bad\nname.txt")
        self.assertBad("unzulässiger Name")

    def test_origin_mismatch(self):
        write(self.build, "robots.txt", b"Sitemap: https://www.deinedomain.de/sitemap.xml\n")
        with self.assertRaises(fd.BuildError):
            fd.check_build_origin(fd.scan_build(self.build), SITE)


class OrderTests(TempBuildCase):
    def test_order(self):
        order = [f.rel for f in fd.upload_order(fd.scan_build(self.build))]
        self.assertEqual(order[-1], ".htaccess")
        self.assertEqual(order[-2], "index.html")
        html = [i for i, r in enumerate(order) if r.endswith(".html")]
        non_html = [i for i, r in enumerate(order) if not r.endswith(".html") and r != ".htaccess"]
        self.assertLess(max(non_html), min(html))


class PlanTests(TempBuildCase):
    def prepared_remote(self):
        remote = FakeRemote()
        remote.dirs |= {ROOT + "/about", ROOT + "/_astro", ROOT + "/uploads", ROOT + "/alt"}
        remote.files.update({
            ROOT + "/index.html": b"old",
            ROOT + "/.htaccess": b"RewriteEngine On\n",
            ROOT + "/fremd.txt": b"keep me",
            ROOT + "/uploads/user.jpg": b"keep",
            ROOT + "/about/extra.html": b"keep",
        })
        return remote

    def test_plan_classifies_and_lists_extras(self):
        remote = self.prepared_remote()
        plan = fd.build_plan(remote, ROOT, fd.scan_build(self.build))
        self.assertIn("index.html", plan.replace_other_size)
        self.assertIn(".htaccess", plan.replace_same_size)
        self.assertIn("404.html", plan.new_files)
        self.assertIn("assets", plan.missing_dirs)
        self.assertIn("assets/images", plan.missing_dirs)
        self.assertLess(plan.missing_dirs.index("assets"), plan.missing_dirs.index("assets/images"))
        self.assertEqual(sorted(plan.extras), ["about/extra.html", "alt/", "fremd.txt", "uploads/"])
        self.assertFalse(plan.conflicts)
        # nie in Extras abgestiegen
        self.assertNotIn(("list_dir", ROOT + "/uploads"), remote.ops)

    def test_type_conflict(self):
        remote = FakeRemote()
        remote.dirs.add(ROOT + "/index.html")
        plan = fd.build_plan(remote, ROOT, fd.scan_build(self.build))
        self.assertTrue(plan.conflicts)

    def test_default_mode_is_readonly(self):
        remote = self.prepared_remote()
        snapshot = (dict(remote.files), set(remote.dirs))
        code, out, err = self.run_main(["--source", self.build], remote=remote, env={k: v for k, v in ENV.items() if k != "DEPLOY_ENABLED"})
        self.assertEqual(code, 0, err)
        self.assertEqual(remote.writes(), [])
        self.assertEqual((remote.files, remote.dirs), snapshot)
        self.assertIn("nichts auf dem Server verändert", out)
        self.assertTrue(remote.closed)

    def test_readonly_wrapper_has_no_write_methods(self):
        wrapper = fd.ReadOnlyRemote(FakeRemote())
        for name in ("store", "rename", "delete", "mkdir"):
            self.assertFalse(hasattr(wrapper, name), name)

    def test_plan_with_missing_root_fails(self):
        remote = FakeRemote()
        remote.dirs.clear()
        code, _, err = self.run_main(["--source", self.build], remote=remote)
        self.assertEqual(code, 1)
        self.assertEqual(remote.writes(), [])

    def test_plan_reports_conflicts_as_error(self):
        remote = FakeRemote()
        remote.dirs.add(ROOT + "/index.html")
        code, out, _ = self.run_main(["--source", self.build], remote=remote)
        self.assertEqual(code, 1)
        self.assertIn("KONFLIKTE", out)


class DeployTests(TempBuildCase):
    def setUp(self):
        super().setUp()
        self.remote = FakeRemote()
        self.remote.dirs |= {ROOT + "/about", ROOT + "/uploads"}
        self.remote.files.update({
            ROOT + "/index.html": b"old",
            ROOT + "/fremd.txt": b"keep me",
            ROOT + "/uploads/user.jpg": b"keep",
        })
        self.web = FakeWeb(self.remote)

    def deploy(self, **kwargs):
        return self.run_main(["--source", self.build, "--deploy"], remote=self.remote, web=self.web, **kwargs)

    def test_refused_without_enabled_flag(self):
        for value in (None, "", "false", "TRUE", "1", "true "):
            env = {k: v for k, v in ENV.items() if k != "DEPLOY_ENABLED"}
            if value is not None:
                env["DEPLOY_ENABLED"] = value
            remote = FakeRemote()
            code, _, err = self.run_main(["--source", self.build, "--deploy"], env=env, remote=remote, web=self.web)
            self.assertEqual(code, 2, value)
            self.assertEqual(remote.ops, [], value)  # nicht einmal verbunden
            self.assertIn("DEPLOY_ENABLED", err)

    def test_missing_credentials(self):
        env = {k: v for k, v in ENV.items() if k != "FTP_PASSWORD"}
        remote = FakeRemote()
        code, _, err = self.run_main(["--source", self.build, "--deploy"], env=env, remote=remote, web=self.web)
        self.assertEqual(code, 2)
        self.assertEqual(remote.ops, [])
        self.assertIn("FTP_PASSWORD", err)

    def test_wrong_remote_dir_never_connects(self):
        remote = FakeRemote()
        code, _, _ = self.run_main(["--source", self.build, "--deploy"], env=dict(ENV, FTP_REMOTE_DIR="/"), remote=remote, web=self.web)
        self.assertEqual(code, 2)
        self.assertEqual(remote.ops, [])

    def test_successful_deploy(self):
        code, out, err = self.deploy()
        self.assertEqual(code, 0, err + out)
        files = self.remote.files
        # Builddateien liegen vollständig vor, gleichnamige wurden ersetzt
        for f in fd.scan_build(self.build):
            with open(f.path, "rb") as fh:
                self.assertEqual(files[ROOT + "/" + f.rel], fh.read(), f.rel)
        # zusätzliche Dateien bleiben
        self.assertEqual(files[ROOT + "/fremd.txt"], b"keep me")
        self.assertEqual(files[ROOT + "/uploads/user.jpg"], b"keep")
        # keine Reste von Proben oder Temp-Dateien
        leftovers = [p for p in files if fd.TMP_PREFIX in p or fd.PROBE_PREFIX in p]
        self.assertEqual(leftovers, [])
        self.assertIn("zusätzliche Serverinhalte unverändert", out)

    def test_probe_before_uploads_and_cleanup(self):
        self.assertEqual(self.deploy()[0], 0)
        writes = self.remote.writes()
        probe_idx = [i for i, op in enumerate(writes) if fd.PROBE_PREFIX in " ".join(op[1:])]
        build_idx = [i for i, op in enumerate(writes) if op[0] == "rename" and fd.PROBE_PREFIX not in op[2]]
        self.assertTrue(probe_idx and build_idx)
        probe_final_delete = [i for i in probe_idx if writes[i][0] == "delete"]
        self.assertEqual(len(probe_final_delete), 1)
        self.assertLess(max(probe_idx), min(build_idx))  # Probe komplett fertig, bevor Dateien ersetzt werden
        self.assertTrue(writes[0][0] == "store" and fd.TMP_PREFIX in writes[0][1])
        # Probe wurde per HTTP abgerufen
        self.assertTrue(any(fd.PROBE_PREFIX in url for url in self.web.urls))

    def test_atomic_temp_then_rename_and_order(self):
        self.assertEqual(self.deploy()[0], 0)
        ops = self.remote.writes()
        renames = [op for op in ops if op[0] == "rename" and fd.PROBE_PREFIX not in op[2]]
        for i, op in enumerate(ops):
            if op[0] == "store":
                nxt = next(o for o in ops[i + 1:] if o[0] == "rename")
                self.assertEqual(nxt[1], op[1])  # jeder Store wird direkt umbenannt
                self.assertTrue(posixpath.basename(op[1]).startswith(fd.TMP_PREFIX))
                self.assertEqual(posixpath.dirname(op[1]), posixpath.dirname(nxt[2]))  # gleicher Ordner
        finals = [op[2][len(ROOT) + 1:] for op in renames]
        self.assertEqual(finals[-1], ".htaccess")
        self.assertEqual(finals[-2], "index.html")
        first_html = min(i for i, r in enumerate(finals) if r.endswith(".html"))
        last_asset = max(i for i, r in enumerate(finals) if not r.endswith(".html") and r != ".htaccess")
        self.assertLess(last_asset, first_html)

    def test_only_own_probe_is_deleted(self):
        self.assertEqual(self.deploy()[0], 0)
        deletes = [op[1] for op in self.remote.ops if op[0] == "delete"]
        self.assertEqual(len(deletes), 1)  # ausschließlich die eigene Probe
        self.assertTrue(posixpath.basename(deletes[0]).startswith(fd.PROBE_PREFIX))
        self.assertIn(ROOT + "/fremd.txt", self.remote.files)

    def test_wrong_http_target_aborts_before_any_update(self):
        wrong = FakeRemote()  # andere Dokumentwurzel: Probe wird nicht ausgeliefert
        web = FakeWeb(wrong, docroot=ROOT)
        before = dict(self.remote.files)
        code, _, err = self.run_main(["--source", self.build, "--deploy"], remote=self.remote, web=web)
        self.assertEqual(code, 1)
        self.assertIn("Webroot nicht bestätigt", err)
        self.assertEqual(self.remote.files, before)  # Probe entfernt, nichts aktualisiert
        self.assertFalse([op for op in self.remote.writes() if op[0] == "rename" and fd.PROBE_PREFIX not in op[2]
                          and not posixpath.basename(op[2]).startswith(fd.PROBE_PREFIX)])
        self.assertNotIn("mkdir", [op[0] for op in self.remote.ops])

    def test_probe_with_wrong_content_is_rejected(self):
        web = FakeWeb(self.remote)
        original = web.__call__

        def tampered(url):
            response = original(url)
            return fd.HttpResponse(response.status, response.content_type, b"anderer Inhalt")

        code, _, err = self.run_main(["--source", self.build, "--deploy"], remote=self.remote, web=tampered)
        self.assertEqual(code, 1)
        self.assertIn("Webroot nicht bestätigt", err)
        self.assertEqual(self.remote.files[ROOT + "/index.html"], b"old")

    def test_server_without_rename_overwrite_aborts_before_update(self):
        self.remote.rename_overwrite = False
        code, _, _ = self.deploy()
        self.assertEqual(code, 1)
        self.assertEqual(self.remote.files[ROOT + "/index.html"], b"old")
        self.assertEqual([p for p in self.remote.files if fd.PROBE_PREFIX in p or fd.TMP_PREFIX in p], [])

    def test_failed_upload_cleans_temp_and_keeps_extras(self):
        self.remote.fail_store_for = "-8"  # 6. Builddatei (Zähler im Temp-Namen)
        code, _, _ = self.deploy()
        self.assertEqual(code, 1)
        self.assertEqual([p for p in self.remote.files if fd.TMP_PREFIX in p or fd.PROBE_PREFIX in p], [])
        self.assertEqual(self.remote.files[ROOT + "/fremd.txt"], b"keep me")
        self.assertEqual(self.remote.files[ROOT + "/uploads/user.jpg"], b"keep")

    def test_conflict_aborts_before_probe(self):
        self.remote.dirs.add(ROOT + "/robots.txt")
        code, _, _ = self.deploy()
        self.assertEqual(code, 1)
        self.assertEqual(self.remote.writes(), [])

    def test_post_check_failure_reports_error(self):
        self.web.htaccess_status = 200
        code, _, err = self.deploy()
        self.assertEqual(code, 1)
        self.assertIn(".htaccess ist öffentlich abrufbar", err)
        self.assertIn("kein Rollback", err)

    def test_post_check_soft_404(self):
        self.web.not_found_status = 200
        code, _, err = self.deploy()
        self.assertEqual(code, 1)
        self.assertIn("statt 404", err)

    def test_password_never_printed(self):
        self.remote.fail_store_for = "-3"
        original_store = self.remote.store

        def leaky(path, fp):
            if "-3" in path:
                raise ftplib.error_perm(f"530 login {PASSWORD} deploy-user")
            return original_store(path, fp)

        self.remote.store = leaky
        code, out, err = self.deploy()
        self.assertEqual(code, 1)
        self.assertNotIn(PASSWORD, out + err)
        self.assertNotIn("deploy-user", out + err)


class OfflineTests(TempBuildCase):
    def test_offline_needs_no_credentials_and_no_remote(self):
        factory = mock.Mock()
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = fd.main(["--source", self.build, "--offline"], {}, remote_factory=factory)
        self.assertEqual(code, 0, err.getvalue())
        factory.assert_not_called()
        self.assertIn("keine Verbindung", out.getvalue())

    def test_offline_rejects_bad_build(self):
        os.remove(os.path.join(self.build, ".htaccess"))
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(fd.main(["--source", self.build, "--offline"], {}), 1)

    def test_plan_without_credentials_hints_offline(self):
        factory = mock.Mock()
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = fd.main(["--source", self.build], {}, remote_factory=factory)
        self.assertEqual(code, 2)
        self.assertIn("--offline", err.getvalue())
        factory.assert_not_called()

    def test_offline_and_deploy_exclusive(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            fd.main(["--offline", "--deploy"], {})


class FtpsClientTests(unittest.TestCase):
    def make(self):
        ftp = mock.MagicMock()
        factory = mock.Mock(return_value=ftp)
        client = fd.FtpsClient(fd.load_config(ENV), ftp_factory=factory)
        return client, ftp, factory

    def test_connect_sequence_and_tls_context(self):
        client, ftp, factory = self.make()
        client.connect()
        context = factory.call_args.kwargs["context"]
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        self.assertGreaterEqual(context.minimum_version, ssl.TLSVersion.TLSv1_2)
        names = [c[0] for c in ftp.method_calls]
        self.assertEqual(names[:5], ["connect", "auth", "login", "prot_p", "set_pasv"])
        ftp.connect.assert_called_with("ftp.example.test", 21)
        ftp.set_pasv.assert_called_with(True)
        ftp.set_debuglevel.assert_not_called()

    def test_connect_failure_closes(self):
        client, ftp, _ = self.make()
        ftp.login.side_effect = ftplib.error_perm("530 Login incorrect")
        with self.assertRaises(ftplib.error_perm):
            client.connect()
        ftp.quit.assert_called_once()

    def test_write_guards(self):
        client, ftp, _ = self.make()
        client.connect()
        tmp = ROOT + "/" + fd.TMP_PREFIX + "x-1"
        client.store(tmp, io.BytesIO(b"x"))
        client.rename(tmp, ROOT + "/index.html")
        client.delete(tmp)
        client.mkdir(ROOT + "/new")
        for call in (
            lambda: client.store(ROOT + "/index.html", io.BytesIO()),  # nicht über Temp
            lambda: client.store("/other.example/" + fd.TMP_PREFIX + "x", io.BytesIO()),
            lambda: client.store(ROOT + "/../x/" + fd.TMP_PREFIX + "x", io.BytesIO()),
            lambda: client.store(ROOT + "-evil/" + fd.TMP_PREFIX + "x", io.BytesIO()),
            lambda: client.rename(ROOT + "/index.html", ROOT + "/other.html"),
            lambda: client.rename(tmp, "/elsewhere/file"),
            lambda: client.delete(ROOT + "/index.html"),
            lambda: client.delete("/"),
            lambda: client.mkdir(ROOT),
            lambda: client.mkdir("/neu"),
            lambda: client.list_dir("/"),
            lambda: client.resolve_dir("/"),
        ):
            with self.assertRaises(fd.DeployError):
                call()
        ftp.storbinary.assert_called_once()
        ftp.rename.assert_called_once()
        ftp.delete.assert_called_once()
        ftp.mkd.assert_called_once()

    def test_list_dir_mlsd(self):
        client, ftp, _ = self.make()
        client.connect()
        ftp.mlsd.return_value = iter([
            (".", {"type": "cdir"}), ("..", {"type": "pdir"}),
            ("a.txt", {"type": "file", "size": "5"}), ("sub", {"type": "dir"}),
            ("link", {"type": "OS.unix=slink:/x"}),
        ])
        entries = client.list_dir(ROOT)
        self.assertEqual(entries["a.txt"], fd.RemoteEntry("file", 5))
        self.assertEqual(entries["sub"].kind, "dir")
        self.assertEqual(entries["link"].kind, "other")

    def test_list_dir_not_found(self):
        client, ftp, _ = self.make()
        client.connect()
        ftp.mlsd.side_effect = ftplib.error_perm("550 No such directory")
        self.assertIsNone(client.list_dir(ROOT + "/x"))

    def test_list_dir_fallback_without_mlsd(self):
        client, ftp, _ = self.make()
        client.connect()
        ftp.mlsd.side_effect = ftplib.error_perm("500 Unknown command")
        ftp.nlst.return_value = [ROOT + "/a.txt", ROOT + "/sub"]

        def cwd(path):
            if path.endswith("/a.txt"):
                raise ftplib.error_perm("550 Not a directory")

        ftp.cwd.side_effect = cwd
        ftp.pwd.return_value = ROOT
        ftp.size.return_value = 7
        entries = client.list_dir(ROOT)
        self.assertEqual(entries["a.txt"], fd.RemoteEntry("file", 7))
        self.assertEqual(entries["sub"].kind, "dir")

    def test_resolve_dir_missing(self):
        client, ftp, _ = self.make()
        client.connect()
        ftp.cwd.side_effect = ftplib.error_perm("550 nope")
        self.assertIsNone(client.resolve_dir(ROOT))


class HttpTests(unittest.TestCase):
    def test_redirects_not_followed(self):
        # Der Handler lehnt Weiterleitungen ab, sodass der 3xx-Status sichtbar bleibt.
        self.assertIsNone(fd._NoRedirect().redirect_request(None, None, 301, "", {}, "http://x"))


if __name__ == "__main__":
    unittest.main()
