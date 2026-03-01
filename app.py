from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = "troque-esta-chave-em-producao"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///farmacia.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


class Section(db.Model):
    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(unique=True, nullable=False)

    usuarios: Mapped[list["User"]] = relationship(back_populates="secao")
    produtos: Mapped[list["Product"]] = relationship(back_populates="secao")


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(nullable=False)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"), nullable=False)

    secao: Mapped[Section] = relationship(back_populates="usuarios")
    produtos: Mapped[list["Product"]] = relationship(back_populates="usuario")

    def set_password(self, senha: str) -> None:
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha: str) -> bool:
        return check_password_hash(self.senha_hash, senha)


class Product(db.Model):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(nullable=False)
    validade: Mapped[date] = mapped_column(nullable=False)
    pre_vencido_ativo: Mapped[bool] = mapped_column(default=False)
    data_inicio_pre_vencido: Mapped[date | None]
    data_retirar_prateleira: Mapped[date | None]
    foto_nome: Mapped[str | None]
    criado_em: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    usuario_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"), nullable=False)

    usuario: Mapped[User] = relationship(back_populates="produtos")
    secao: Mapped[Section] = relationship(back_populates="produtos")

    @property
    def status(self) -> str:
        hoje = date.today()
        if self.validade < hoje:
            return "Vencido"
        if self.pre_vencido_ativo and self.data_inicio_pre_vencido and self.data_inicio_pre_vencido <= hoje:
            return "Pré-vencido"
        return "OK"


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return db.session.get(User, int(user_id))


@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename: str):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form["nome"].strip()
        email = request.form["email"].strip().lower()
        senha = request.form["senha"]
        section_nome = request.form["secao"].strip()

        if not all([nome, email, senha, section_nome]):
            flash("Preencha todos os campos.", "erro")
            return redirect(url_for("cadastro"))

        if User.query.filter_by(email=email).first():
            flash("E-mail já cadastrado.", "erro")
            return redirect(url_for("cadastro"))

        secao = Section.query.filter_by(nome=section_nome).first()
        if not secao:
            secao = Section(nome=section_nome)
            db.session.add(secao)
            db.session.flush()

        usuario = User(nome=nome, email=email, secao=secao)
        usuario.set_password(senha)
        db.session.add(usuario)
        db.session.commit()
        flash("Cadastro realizado com sucesso. Faça login.", "sucesso")
        return redirect(url_for("login"))

    return render_template("cadastro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        senha = request.form["senha"]

        usuario = User.query.filter_by(email=email).first()
        if not usuario or not usuario.check_password(senha):
            flash("Credenciais inválidas.", "erro")
            return redirect(url_for("login"))

        login_user(usuario)
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    produtos = (
        Product.query.filter_by(usuario_id=current_user.id)
        .order_by(Product.validade.asc())
        .all()
    )
    secoes = Section.query.order_by(Section.nome.asc()).all()
    return render_template("dashboard.html", produtos=produtos, secoes=secoes)


def _parse_date(field_name: str) -> date | None:
    valor = request.form.get(field_name, "").strip()
    if not valor:
        return None
    return date.fromisoformat(valor)


@app.route("/produtos", methods=["POST"])
@login_required
def criar_produto():
    nome = request.form["nome"].strip()
    validade = _parse_date("validade")
    section_id = int(request.form["section_id"])
    pre_vencido_ativo = request.form.get("pre_vencido_ativo") == "on"
    data_inicio_pre_vencido = _parse_date("data_inicio_pre_vencido")
    data_retirar_prateleira = _parse_date("data_retirar_prateleira")

    if not nome or not validade:
        flash("Nome e data de validade são obrigatórios.", "erro")
        return redirect(url_for("dashboard"))

    if pre_vencido_ativo and not data_inicio_pre_vencido:
        flash("Defina a data de início do pré-vencido.", "erro")
        return redirect(url_for("dashboard"))

    secao = db.session.get(Section, section_id)
    if not secao:
        flash("Seção inválida.", "erro")
        return redirect(url_for("dashboard"))

    foto = request.files.get("foto")
    foto_nome = None
    if foto and foto.filename:
        extensao = Path(foto.filename).suffix.lower()
        foto_nome = f"{uuid4().hex}{extensao}"
        foto.save(UPLOAD_DIR / foto_nome)

    produto = Product(
        nome=nome,
        validade=validade,
        pre_vencido_ativo=pre_vencido_ativo,
        data_inicio_pre_vencido=data_inicio_pre_vencido,
        data_retirar_prateleira=data_retirar_prateleira,
        foto_nome=foto_nome,
        usuario=current_user,
        secao=secao,
    )
    db.session.add(produto)
    db.session.commit()
    flash("Produto cadastrado.", "sucesso")
    return redirect(url_for("dashboard"))


@app.route("/api/alertas")
@login_required
def api_alertas():
    produtos = Product.query.filter_by(usuario_id=current_user.id).all()
    vencidos = [p for p in produtos if p.status == "Vencido"]
    pre_vencidos = [p for p in produtos if p.status == "Pré-vencido"]

    dados = {
        "total": len(produtos),
        "vencidos": len(vencidos),
        "pre_vencidos": len(pre_vencidos),
        "itens_criticos": [
            {
                "nome": p.nome,
                "status": p.status,
                "validade": p.validade.strftime("%d/%m/%Y"),
                "secao": p.secao.nome,
            }
            for p in sorted(vencidos + pre_vencidos, key=lambda item: item.validade)
        ],
    }
    return jsonify(dados)


@app.cli.command("init-db")
def init_db_command():
    db.create_all()
    print("Banco de dados inicializado.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
