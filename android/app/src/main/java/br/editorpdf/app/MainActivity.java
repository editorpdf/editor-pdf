package br.editorpdf.app;

import android.app.Activity;
import android.content.ContentValues;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.CancellationSignal;
import android.os.Environment;
import android.os.ParcelFileDescriptor;
import android.print.PageRange;
import android.print.PrintAttributes;
import android.print.PrintDocumentAdapter;
import android.print.PrintDocumentInfo;
import android.print.PrintManager;
import android.provider.MediaStore;
import android.provider.OpenableColumns;
import android.util.Base64;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.core.content.FileProvider;
import androidx.webkit.WebViewAssetLoader;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Editor de PDF para Android: a mesma página do computador, rodando numa WebView com o motor MuPDF.js.
 * Os arquivos do app são servidos de https://appassets.androidplatform.net/assets/www/ (nada vem da internet).
 * A ponte "AndroidApp" salva na pasta Downloads e compartilha; um PDF aberto pelo "Abrir com" é entregue em /recebido/.
 */
public class MainActivity extends Activity {
    private static final String ORIGEM = "https://appassets.androidplatform.net";
    private static final String INICIO = ORIGEM + "/assets/www/index.html";
    private static final int ESCOLHER_ARQUIVO = 10;
    private static final Map<String, String> TIPOS = new HashMap<>();
    static {
        TIPOS.put("html", "text/html");
        TIPOS.put("js", "text/javascript");
        TIPOS.put("mjs", "text/javascript");
        TIPOS.put("wasm", "application/wasm");
        TIPOS.put("css", "text/css");
        TIPOS.put("json", "application/json");
        TIPOS.put("png", "image/png");
        TIPOS.put("svg", "image/svg+xml");
    }

    private WebView web;
    private ValueCallback<Uri[]> escolha;
    private Uri recebido;
    private String nomeRecebido = "documento.pdf";

    @Override
    protected void onCreate(Bundle salvo) {
        super.onCreate(salvo);
        // só na versão de teste (debug): permite inspecionar a página pelo computador
        if ((getApplicationInfo().flags & android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0) WebView.setWebContentsDebuggingEnabled(true);
        web = new WebView(this);
        setContentView(web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setTextZoom(100);
        s.setSupportZoom(false);

        WebViewAssetLoader carregador = new WebViewAssetLoader.Builder()
                .addPathHandler("/assets/", this::arquivoDoApp)
                .addPathHandler("/recebido/", caminho -> arquivoRecebido())
                .build();

        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest req) {
                return carregador.shouldInterceptRequest(req.getUrl());
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest req) {
                Uri u = req.getUrl();
                if (ORIGEM.equals(u.getScheme() + "://" + u.getHost())) return false;
                try { startActivity(new Intent(Intent.ACTION_VIEW, u)); } catch (Exception ignorado) { }
                return true;  // links externos abrem no navegador do celular
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb, FileChooserParams p) {
                if (escolha != null) escolha.onReceiveValue(null);
                escolha = cb;
                Intent i = new Intent(Intent.ACTION_GET_CONTENT);
                i.addCategory(Intent.CATEGORY_OPENABLE);
                String[] tipos = p.getAcceptTypes();
                List<String> mimes = new ArrayList<>();
                for (String t : tipos) for (String x : t.split(",")) {
                    x = x.trim();
                    if (x.equals(".pdf")) x = "application/pdf";
                    else if (x.startsWith(".")) x = "image/*";
                    if (!x.isEmpty() && !mimes.contains(x)) mimes.add(x);
                }
                i.setType(mimes.size() == 1 ? mimes.get(0) : "*/*");
                if (mimes.size() > 1) i.putExtra(Intent.EXTRA_MIME_TYPES, mimes.toArray(new String[0]));
                i.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, p.getMode() == FileChooserParams.MODE_OPEN_MULTIPLE);
                try {
                    startActivityForResult(Intent.createChooser(i, "Escolher arquivo"), ESCOLHER_ARQUIVO);
                } catch (Exception e) {
                    escolha = null;
                    return false;
                }
                return true;
            }
        });
        web.addJavascriptInterface(new Ponte(), "AndroidApp");

        boolean temArquivo = receber(getIntent());
        web.loadUrl(INICIO + (temArquivo ? "?recebido=1" : ""));
    }

    /** Arquivos do app (pasta assets/www), com o tipo certo para módulos JavaScript e WebAssembly. */
    private WebResourceResponse arquivoDoApp(String caminho) {
        try {
            InputStream in = getAssets().open(caminho);
            String ext = caminho.contains(".") ? caminho.substring(caminho.lastIndexOf('.') + 1).toLowerCase() : "";
            String tipo = TIPOS.containsKey(ext) ? TIPOS.get(ext) : "application/octet-stream";
            return new WebResourceResponse(tipo, tipo.startsWith("text/") ? "utf-8" : null, in);
        } catch (IOException e) {
            return new WebResourceResponse("text/plain", "utf-8", 404, "Not Found", null, null);
        }
    }

    /** O PDF que outro app mandou abrir. */
    private WebResourceResponse arquivoRecebido() {
        try {
            if (recebido == null) throw new IOException("nada recebido");
            return new WebResourceResponse("application/pdf", null, getContentResolver().openInputStream(recebido));
        } catch (Exception e) {
            return new WebResourceResponse("text/plain", "utf-8", 404, "Not Found", null, null);
        }
    }

    private boolean receber(Intent it) {
        if (it == null) return false;
        Uri u = null;
        if (Intent.ACTION_VIEW.equals(it.getAction())) u = it.getData();
        else if (Intent.ACTION_SEND.equals(it.getAction())) u = it.getParcelableExtra(Intent.EXTRA_STREAM);
        if (u == null) return false;
        recebido = u;
        nomeRecebido = nomeDe(u);
        return true;
    }

    private String nomeDe(Uri u) {
        String nome = null;
        try (Cursor c = getContentResolver().query(u, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) {
            if (c != null && c.moveToFirst()) nome = c.getString(0);
        } catch (Exception ignorado) { }
        if (nome == null) nome = u.getLastPathSegment();
        if (nome == null || nome.isEmpty()) nome = "documento.pdf";
        if (!nome.toLowerCase().endsWith(".pdf")) nome += ".pdf";
        return nome;
    }

    @Override
    protected void onNewIntent(Intent it) {
        super.onNewIntent(it);
        if (receber(it)) web.evaluateJavascript("window.abrirRecebido&&abrirRecebido()", null);
    }

    @Override
    protected void onActivityResult(int pedido, int resultado, Intent dados) {
        super.onActivityResult(pedido, resultado, dados);
        if (pedido != ESCOLHER_ARQUIVO || escolha == null) return;
        Uri[] r = null;
        if (resultado == RESULT_OK && dados != null) {
            if (dados.getClipData() != null) {
                r = new Uri[dados.getClipData().getItemCount()];
                for (int i = 0; i < r.length; i++) r[i] = dados.getClipData().getItemAt(i).getUri();
            } else if (dados.getData() != null) {
                r = new Uri[]{dados.getData()};
            }
        }
        escolha.onReceiveValue(r);
        escolha = null;
    }

    @Override
    @SuppressWarnings("deprecation")
    public void onBackPressed() {
        // o editor decide: fecha janelas, volta para o início... e só sai do app na tela inicial
        web.evaluateJavascript("window.voltarAndroid?voltarAndroid():'sair'", v -> {
            if ("\"sair\"".equals(v)) finish();
        });
    }

    /** Ponte chamada pela página (window.AndroidApp). */
    private class Ponte {
        @JavascriptInterface
        public String nomeRecebido() { return nomeRecebido; }

        /** Salva na pasta Downloads/Editor de PDF. Devolve o caminho mostrado ao usuário. */
        @JavascriptInterface
        public String salvar(String nome, String b64, String mime) {
            byte[] dados = Base64.decode(b64, Base64.DEFAULT);
            nome = limpar(nome);
            try {
                if (Build.VERSION.SDK_INT >= 29) {
                    ContentValues cv = new ContentValues();
                    cv.put(MediaStore.Downloads.DISPLAY_NAME, nome);
                    cv.put(MediaStore.Downloads.MIME_TYPE, mime);
                    cv.put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/Editor de PDF");
                    Uri u = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, cv);
                    if (u == null) throw new IOException("sem acesso a Downloads");
                    try (OutputStream out = getContentResolver().openOutputStream(u)) { out.write(dados); }
                } else {
                    File pasta = new File(getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS), "");
                    pasta.mkdirs();
                    try (FileOutputStream out = new FileOutputStream(new File(pasta, nome))) { out.write(dados); }
                    return "ok:" + pasta.getAbsolutePath();
                }
                return "ok:Downloads/Editor de PDF";
            } catch (Exception e) {
                return "erro:" + e.getMessage();
            }
        }

        /** Abre no navegador o download de uma versão nova ou os links de "Sobre e licenças" (só https). */
        @JavascriptInterface
        public void abrirLink(String url) {
            if (url == null || !url.startsWith("https://")) return;
            runOnUiThread(() -> {
                try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url))); } catch (Exception ignored) { }
            });
        }

        /** Manda o PDF para a impressão do Android (impressoras da rede, Wi-Fi Direct, "Salvar como PDF"...). */
        @JavascriptInterface
        public void imprimir(String nome, String b64) {
            final byte[] dados = Base64.decode(b64, Base64.DEFAULT);
            final String titulo = limpar(nome);
            runOnUiThread(() -> {
                PrintManager pm = (PrintManager) getSystemService(PRINT_SERVICE);
                pm.print(titulo, new PrintDocumentAdapter() {
                    @Override
                    public void onLayout(PrintAttributes antes, PrintAttributes novos, CancellationSignal cancelar,
                                         LayoutResultCallback cb, Bundle extras) {
                        if (cancelar.isCanceled()) { cb.onLayoutCancelled(); return; }
                        cb.onLayoutFinished(new PrintDocumentInfo.Builder(titulo)
                                .setContentType(PrintDocumentInfo.CONTENT_TYPE_DOCUMENT).build(), true);
                    }

                    @Override
                    public void onWrite(PageRange[] paginas, ParcelFileDescriptor destino, CancellationSignal cancelar,
                                        WriteResultCallback cb) {
                        try (OutputStream out = new FileOutputStream(destino.getFileDescriptor())) {
                            out.write(dados);
                            cb.onWriteFinished(new PageRange[]{PageRange.ALL_PAGES});
                        } catch (Exception e) {
                            cb.onWriteFailed(e.getMessage());
                        }
                    }
                }, null);
            });
        }

        /** Abre a janela de compartilhar do Android (WhatsApp, e-mail, Drive...). */
        @JavascriptInterface
        public void compartilhar(String nome, String b64, String mime) {
            try {
                File pasta = new File(getCacheDir(), "compartilhar");
                pasta.mkdirs();
                File f = new File(pasta, limpar(nome));
                try (FileOutputStream out = new FileOutputStream(f)) { out.write(Base64.decode(b64, Base64.DEFAULT)); }
                Uri u = FileProvider.getUriForFile(MainActivity.this, "br.editorpdf.app.arquivos", f);
                Intent i = new Intent(Intent.ACTION_SEND);
                i.setType(mime);
                i.putExtra(Intent.EXTRA_STREAM, u);
                i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                runOnUiThread(() -> startActivity(Intent.createChooser(i, "Compartilhar")));
            } catch (Exception ignorado) { }
        }

        private String limpar(String nome) {
            String n = nome == null ? "arquivo" : nome.replaceAll("[\\\\/:*?\"<>|]", "_");
            return n.isEmpty() ? "arquivo" : n;
        }
    }
}
