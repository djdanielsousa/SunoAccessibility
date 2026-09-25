# -*- coding: UTF-8 -*-
"""Small, conservative accessibility fixes for suno.com."""

import codecs
from datetime import datetime
import os

import addonHandler
import api
import config
import controlTypes
import globalPluginHandler
import gui
import languageHandler
import ui
import wx
from logHandler import log

try:
	from gui import guiHelper, settingsDialogs
except ImportError:
	guiHelper = None
	settingsDialogs = None

addonHandler.initTranslation()

config.conf.spec["sunoAccessibility"] = {
	"automaticDiagnostics": "boolean(default=False)",
	"unnamedButtonsOnly": "boolean(default=True)",
	"announceAutomaticSave": "boolean(default=True)",
	"showManualConfirmation": "boolean(default=True)",
	"avoidDuplicates": "boolean(default=True)",
	"captureControlImage": "boolean(default=True)",
	"announceGenerationStatus": "boolean(default=True)",
}

_BROWSERS = {"chrome", "msedge", "firefox", "brave", "vivaldi"}

# NVDA 2021.2 introduced the Role enumeration. Older releases, including
# NVDA 2017.1, expose ROLE_* constants directly in controlTypes.
_ROLE_CONTAINER = getattr(controlTypes, "Role", controlTypes)
_ROLE_LINK = getattr(_ROLE_CONTAINER, "LINK", getattr(controlTypes, "ROLE_LINK", None))
_ROLE_RADIOBUTTON = getattr(
	_ROLE_CONTAINER,
	"RADIOBUTTON",
	getattr(controlTypes, "ROLE_RADIOBUTTON", None),
)
_ROLE_BUTTON = getattr(_ROLE_CONTAINER, "BUTTON", getattr(controlTypes, "ROLE_BUTTON", None))

try:
	_TEXT_TYPE = unicode
except NameError:
	_TEXT_TYPE = str


def _attrs(obj):
	try:
		return obj.IA2Attributes or {}
	except Exception:
		return {}


def _text(value):
	try:
		return _TEXT_TYPE(value or "").strip()
	except Exception:
		return ""


def _diagnosticPath():
	home = os.path.expanduser("~")
	documents = os.path.join(home, "Documents")
	base = documents if os.path.isdir(documents) else home
	return os.path.join(base, "SunoAccessibility-diagnostico.txt")


def _manualPath():
	"""Find the localized manual, falling back to English."""
	try:
		addonPath = addonHandler.getCodeAddon().path
	except Exception:
		return None
	try:
		language = _text(languageHandler.getLanguage()).replace("-", "_")
	except Exception:
		language = "en"
	candidates = [language]
	if "_" in language:
		candidates.append(language.split("_", 1)[0])
	candidates.extend(("en", "pt_PT"))
	for candidate in candidates:
		path = os.path.join(addonPath, "doc", candidate, "readme.html")
		if os.path.isfile(path):
			return path
	return None


def _safeGet(obj, attribute):
	try:
		return getattr(obj, attribute, None)
	except Exception:
		return None


def _objectSummary(label, obj):
	if not obj:
		return u"{0}: inexistente".format(label)
	attrs = _attrs(obj)
	interesting = []
	for key in (
		"tag", "aria-label", "title", "placeholder", "value", "href",
		"id", "class", "data-testid", "data-button-id", "xml-roles",
	):
		value = _text(attrs.get(key))
		if value:
			interesting.append(u"{0}={1}".format(key, value))
	return u"{0}: nome={1}; função={2}; descrição={3}; localização={4}; estados={5}; {6}".format(
		label,
		_text(_safeGet(obj, "name")) or u"sem nome",
		_text(_safeGet(obj, "role")) or u"desconhecida",
		_text(_safeGet(obj, "description")) or u"nenhuma",
		_text(_safeGet(obj, "location")) or u"desconhecida",
		_text(_safeGet(obj, "states")) or u"nenhum",
		u"; ".join(interesting) or u"sem atributos identificadores",
	)


def _walkRelated(obj, attribute, limit):
	result = []
	seen = set()
	current = _safeGet(obj, attribute)
	while current and len(result) < limit and id(current) not in seen:
		seen.add(id(current))
		result.append(current)
		current = _safeGet(current, attribute)
	return result


def _diagnosticParts(obj):
	attrs = _attrs(obj)
	return [
		_("Nome: {value}").format(value=_text(getattr(obj, "name", "")) or _("sem nome")),
		_("Função: {value}").format(value=_text(getattr(obj, "role", ""))),
		_("Etiqueta ARIA: {value}").format(value=_text(attrs.get("aria-label")) or _("nenhuma")),
		_("Título: {value}").format(value=_text(attrs.get("title")) or _("nenhum")),
		_("Marcador: {value}").format(value=_text(attrs.get("placeholder")) or _("nenhum")),
	]


def _diagnosticSignature(obj):
	attrs = _attrs(obj)
	return u"|".join((
		_text(_safeGet(obj, "name")), _text(_safeGet(obj, "role")),
		_text(_safeGet(obj, "location")), _text(attrs.get("class")),
		_text(attrs.get("data-testid")), _text(attrs.get("data-button-id")),
	))


def _locationParts(obj):
	location = _safeGet(obj, "location")
	if not location:
		return None
	try:
		return (int(location.left), int(location.top), int(location.width), int(location.height))
	except Exception:
		try:
			return tuple(int(value) for value in location[:4])
		except Exception:
			return None


def _captureControlImage(obj):
	"""Capture the control plus context directly from the rendered screen."""
	location = _locationParts(obj)
	if not location:
		return None, _("localização do controlo indisponível")
	left, top, width, height = location
	if width <= 0 or height <= 0:
		return None, _("dimensões do controlo inválidas")
	paddingX = 80
	paddingY = 45
	x = max(0, left - paddingX)
	y = max(0, top - paddingY)
	captureWidth = max(1, width + paddingX * 2)
	captureHeight = max(1, height + paddingY * 2)
	folder = os.path.join(os.path.dirname(_diagnosticPath()), "SunoAccessibility-diagnosticos")
	if not os.path.isdir(folder):
		os.makedirs(folder)
	stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
	path = os.path.join(folder, "controlo-{0}-{1}-{2}.png".format(stamp, left, top))
	try:
		screen = wx.ScreenDC()
		try:
			bitmap = wx.Bitmap(captureWidth, captureHeight)
		except Exception:
			bitmap = wx.EmptyBitmap(captureWidth, captureHeight)
		memory = wx.MemoryDC()
		memory.SelectObject(bitmap)
		memory.Blit(0, 0, captureWidth, captureHeight, screen, x, y)
		memory.SelectObject(wx.NullBitmap)
		if not bitmap.SaveFile(path, wx.BITMAP_TYPE_PNG):
			return None, _("não foi possível guardar a imagem PNG")
		return path, None
	except Exception as error:
		log.error("Falha ao capturar a imagem do controlo do Suno", exc_info=True)
		return None, _text(error)


def _saveDiagnostic(obj, parts):
	path = _diagnosticPath()
	isNew = not os.path.exists(path)
	attrs = _attrs(obj)
	imagePath = None
	imageError = None
	if config.conf["sunoAccessibility"]["captureControlImage"]:
		imagePath, imageError = _captureControlImage(obj)
	with codecs.open(path, "a", "utf-8") as report:
		if isNew:
			report.write(u"\ufeffDIAGNÓSTICO — ACESSIBILIDADE PARA SUNO AI\r\n")
		report.write(u"\r\nData: {0}\r\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
		for part in parts:
			report.write(_text(part) + u"\r\n")
		if imagePath:
			report.write(u"Imagem do controlo: {0}\r\n".format(_text(imagePath)))
		elif imageError:
			report.write(u"Imagem do controlo: não capturada — {0}\r\n".format(_text(imageError)))
		report.write(u"Atributos IA2:\r\n")
		for key in sorted(attrs):
			report.write(u"  {0}: {1}\r\n".format(_text(key), _text(attrs.get(key))))
		report.write(u"Contexto na árvore de acessibilidade:\r\n")
		for index, related in enumerate(_walkRelated(obj, "previous", 3), 1):
			report.write(_objectSummary(u"  Anterior {0}".format(index), related) + u"\r\n")
		for index, related in enumerate(_walkRelated(obj, "next", 3), 1):
			report.write(_objectSummary(u"  Seguinte {0}".format(index), related) + u"\r\n")
		for index, related in enumerate(_walkRelated(obj, "parent", 5), 1):
			report.write(_objectSummary(u"  Pai {0}".format(index), related) + u"\r\n")
		child = _safeGet(obj, "firstChild")
		children = []
		seenChildren = set()
		while child and len(children) < 5 and id(child) not in seenChildren:
			seenChildren.add(id(child))
			children.append(child)
			child = _safeGet(child, "next")
		if children:
			for index, related in enumerate(children, 1):
				report.write(_objectSummary(u"  Filho {0}".format(index), related) + u"\r\n")
		else:
			report.write(u"  Filhos: nenhum\r\n")
		report.write(u"----------------------------------------\r\n")
	return path


def _inSuno(obj):
	"""Limit every modification to browser objects belonging to suno.com."""
	try:
		if obj.appModule.appName.lower() not in _BROWSERS:
			return False
	except Exception:
		return False

	current = obj
	for _unused in range(18):
		if not current:
			break
		attrs = _attrs(current)
		for key in ("doc-url", "document-url", "url", "href"):
			if "suno.com" in _text(attrs.get(key)).lower():
				return True
		for value in (
			getattr(current, "windowText", ""),
			getattr(current, "description", ""),
		):
			if "suno" in _text(value).lower():
				return True
		try:
			current = current.parent
		except Exception:
			break
	return False


def _role(obj, expected):
	try:
		return obj.role == expected
	except Exception:
		return False


def _nearbyName(obj, attribute):
	neighbor = _safeGet(obj, attribute)
	return _text(_safeGet(neighbor, "name")).lower() if neighbor else ""


def _miniReactionPosition(obj):
	"""Return the position after Play Count for Suno's reaction buttons."""
	current = obj
	for position in range(1, 4):
		current = _safeGet(current, "previous")
		if not current:
			return 0
		if _text(_safeGet(current, "name")).lower() == "play count":
			return position
		classes = _text(_attrs(current).get("class"))
		if not (_role(current, _ROLE_BUTTON) and "hxc-btn-size-mini" in classes):
			return 0
	return 0


def _generationStatus(obj):
	"""Detect explicit Suno generation messages without matching old songs."""
	attrs = _attrs(obj)
	content = u" ".join(_text(value).lower() for value in (
		_safeGet(obj, "name"), _safeGet(obj, "value"),
		_safeGet(obj, "description"), attrs.get("aria-label"),
		attrs.get("title"), attrs.get("value"),
	))
	inProgress = (
		"creating your song", "generating your song", "making your song",
		"song is being created", "song is being generated", "generation in progress",
		"creating...", "generating...", "queued for generation",
		"a criar a sua música", "a gerar a sua música", "criação em curso",
		"creando tu canción", "generando tu canción", "generación en curso",
		"dein song wird erstellt", "dein song wird generiert",
		"création de votre chanson", "génération de votre chanson",
		"creazione del brano", "generazione del brano",
		"je nummer wordt gemaakt", "je nummer wordt gegenereerd",
	)
	complete = (
		"your song is ready", "song generated successfully", "song created successfully",
		"generation complete", "generation completed", "creation complete",
		"a sua música está pronta", "música gerada com sucesso",
		"tu canción está lista", "canción generada correctamente",
		"dein song ist fertig", "song erfolgreich generiert",
		"votre chanson est prête", "chanson générée avec succès",
		"il tuo brano è pronto", "brano generato correttamente",
		"je nummer is klaar", "nummer succesvol gegenereerd",
	)
	if any(marker in content for marker in inProgress):
		return "progress"
	if any(marker in content for marker in complete):
		return "complete"
	return ""


def _labelFor(obj):
	"""Return a label only where the purpose can be identified reliably."""
	attrs = _attrs(obj)
	tag = _text(attrs.get("tag")).lower()
	href = _text(attrs.get("href")).lower().rstrip("/")
	title = _text(attrs.get("title"))
	placeholder = _text(attrs.get("placeholder"))
	value = _text(attrs.get("value")).lower()
	classes = _text(attrs.get("class"))

	if title:
		return title
	if placeholder:
		translations = {
			"chat to make music": _("Descreva a música que deseja criar"),
		}
		return translations.get(placeholder.lower(), placeholder)
	if _role(obj, _ROLE_LINK) and (href.endswith("suno.com/home") or href == "/home"):
		return _("Suno — Página inicial")
	if _role(obj, _ROLE_RADIOBUTTON):
		if value == "month":
			return _("Faturação mensal")
		if value == "year":
			return _("Faturação anual, poupa 20 por cento")
	if _role(obj, _ROLE_BUTTON):
		# These three icon-only buttons follow Play Count in a fixed order.
		if tag == "button" and "hxc-btn-size-mini" in classes and "hxc-btn-icon-only" in classes:
			reactionLabels = {
				1: _("Comentários"),
				2: _("Gostei"),
				3: _("Não gostei"),
			}
			label = reactionLabels.get(_miniReactionPosition(obj))
			if label:
				return label
		# The image diagnostic confirmed this arrow is the Share button.
		if (
			tag == "button"
			and "hxc-btn-variant-standard-legacy" in classes
			and "hxc-btn-icon-only" in classes
			and _nearbyName(obj, "previous") == "add to playlist"
			and _nearbyName(obj, "next") == "play"
		):
			return _("Partilhar")
		# The plus button beside the public creation prompt.
		if _text(attrs.get("data-context-menu-trigger")).lower() == "true" and "h-9" in classes and "w-9" in classes:
			return _("Adicionar áudio ou referência")
		if tag == "button" and _text(attrs.get("aria-haspopup")) == "menu":
			return _("Abrir menu")
	return ""


if settingsDialogs:
	class SunoSettingsPanel(settingsDialogs.SettingsPanel):
		title = _("Suno AI")

		def makeSettings(self, settingsSizer):
			helper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
			self.automaticDiagnostics = helper.addItem(wx.CheckBox(self, label=_(
				"Criar diagnóstico automaticamente ao focar botões do Suno"
			)))
			self.unnamedButtonsOnly = helper.addItem(wx.CheckBox(self, label=_(
				"Diagnosticar apenas botões sem etiqueta"
			)))
			self.announceAutomaticSave = helper.addItem(wx.CheckBox(self, label=_(
				"Anunciar cada diagnóstico automático guardado"
			)))
			self.showManualConfirmation = helper.addItem(wx.CheckBox(self, label=_(
				"Mostrar diálogo com OK após diagnóstico manual"
			)))
			self.avoidDuplicates = helper.addItem(wx.CheckBox(self, label=_(
				"Evitar diagnósticos automáticos repetidos"
			)))
			self.captureControlImage = helper.addItem(wx.CheckBox(self, label=_(
				"Guardar uma imagem do botão e da área envolvente"
			)))
			self.announceGenerationStatus = helper.addItem(wx.CheckBox(self, label=_(
				"Anunciar o início e a conclusão da geração de músicas"
			)))
			section = config.conf["sunoAccessibility"]
			self.automaticDiagnostics.SetValue(section["automaticDiagnostics"])
			self.unnamedButtonsOnly.SetValue(section["unnamedButtonsOnly"])
			self.announceAutomaticSave.SetValue(section["announceAutomaticSave"])
			self.showManualConfirmation.SetValue(section["showManualConfirmation"])
			self.avoidDuplicates.SetValue(section["avoidDuplicates"])
			self.captureControlImage.SetValue(section["captureControlImage"])
			self.announceGenerationStatus.SetValue(section["announceGenerationStatus"])

		def onSave(self):
			section = config.conf["sunoAccessibility"]
			section["automaticDiagnostics"] = self.automaticDiagnostics.IsChecked()
			section["unnamedButtonsOnly"] = self.unnamedButtonsOnly.IsChecked()
			section["announceAutomaticSave"] = self.announceAutomaticSave.IsChecked()
			section["showManualConfirmation"] = self.showManualConfirmation.IsChecked()
			section["avoidDuplicates"] = self.avoidDuplicates.IsChecked()
			section["captureControlImage"] = self.captureControlImage.IsChecked()
			section["announceGenerationStatus"] = self.announceGenerationStatus.IsChecked()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = _("Acessibilidade para Suno AI")

	def __init__(self):
		super(GlobalPlugin, self).__init__()
		self._lastSunoObject = None
		self._lastAutomaticSignature = None
		self._generationInProgress = False
		if settingsDialogs and SunoSettingsPanel not in settingsDialogs.NVDASettingsDialog.categoryClasses:
			settingsDialogs.NVDASettingsDialog.categoryClasses.append(SunoSettingsPanel)
		self._toolsMenu = gui.mainFrame.sysTrayIcon.toolsMenu
		self._sunoMenu = wx.Menu()
		self._manualMenuItem = self._sunoMenu.Append(wx.ID_ANY, _("Abrir manual..."))
		self._sunoMenu.AppendSeparator()
		self._diagnosticMenuItem = self._sunoMenu.Append(
			wx.ID_ANY,
			_("Criar diagnóstico detalhado do último controlo sem etiqueta..."),
		)
		if hasattr(self._toolsMenu, "AppendSubMenu"):
			self._sunoSubmenuItem = self._toolsMenu.AppendSubMenu(
				self._sunoMenu,
				_("Suno AI"),
			)
		else:
			self._sunoSubmenuItem = self._toolsMenu.AppendMenu(
				wx.NewId(),
				_("Suno AI"),
				self._sunoMenu,
			)
		gui.mainFrame.sysTrayIcon.Bind(
			wx.EVT_MENU,
			self._onOpenManual,
			self._manualMenuItem,
		)
		gui.mainFrame.sysTrayIcon.Bind(
			wx.EVT_MENU,
			self._onCreateDiagnostic,
			self._diagnosticMenuItem,
		)

	def terminate(self):
		if settingsDialogs and SunoSettingsPanel in settingsDialogs.NVDASettingsDialog.categoryClasses:
			settingsDialogs.NVDASettingsDialog.categoryClasses.remove(SunoSettingsPanel)
		try:
			gui.mainFrame.sysTrayIcon.Unbind(
				wx.EVT_MENU,
				handler=self._onOpenManual,
				source=self._manualMenuItem,
			)
		except Exception:
			pass
		try:
			gui.mainFrame.sysTrayIcon.Unbind(
				wx.EVT_MENU,
				handler=self._onCreateDiagnostic,
				source=self._diagnosticMenuItem,
			)
		except Exception:
			pass
		try:
			self._toolsMenu.DestroyItem(self._sunoSubmenuItem)
		except Exception:
			try:
				self._toolsMenu.Remove(self._sunoSubmenuItem)
			except Exception:
				pass
		try:
			super(GlobalPlugin, self).terminate()
		except AttributeError:
			# Some very old NVDA releases do not expose terminate on the base class.
			pass

	def event_gainFocus(self, obj, nextHandler):
		nextHandler()
		try:
			# Preserve only genuinely unnamed controls. Named fields opened while
			# navigating menus (for example the emoji search box) must not replace
			# the control the user intends to diagnose.
			if _inSuno(obj) and not _text(getattr(obj, "name", "")):
				self._lastSunoObject = obj
			if not _inSuno(obj) or not _role(obj, _ROLE_BUTTON):
				return
			section = config.conf["sunoAccessibility"]
			if not section["automaticDiagnostics"]:
				return
			if section["unnamedButtonsOnly"] and _text(getattr(obj, "name", "")):
				return
			signature = _diagnosticSignature(obj)
			if section["avoidDuplicates"] and signature == self._lastAutomaticSignature:
				return
			_saveDiagnostic(obj, [_("Diagnóstico automático")] + _diagnosticParts(obj))
			self._lastAutomaticSignature = signature
			if section["announceAutomaticSave"]:
				ui.message(_("Diagnóstico automático do Suno guardado"))
		except Exception:
			log.error("Falha no diagnóstico automático do Suno", exc_info=True)

	def event_NVDAObject_init(self, obj):
		try:
			if not _inSuno(obj):
				return
			if not _text(getattr(obj, "name", "")):
				label = _labelFor(obj)
				if label:
					obj.name = label
			self._checkGenerationStatus(obj)
		except Exception:
			log.debugWarning("Falha ao etiquetar um controlo do Suno", exc_info=True)

	def event_nameChange(self, obj, nextHandler):
		nextHandler()
		self._checkGenerationStatus(obj)

	def event_valueChange(self, obj, nextHandler):
		nextHandler()
		self._checkGenerationStatus(obj)

	def event_stateChange(self, obj, nextHandler):
		nextHandler()
		self._checkGenerationStatus(obj)

	def event_show(self, obj, nextHandler):
		nextHandler()
		self._checkGenerationStatus(obj)

	def _checkGenerationStatus(self, obj):
		try:
			if not config.conf["sunoAccessibility"]["announceGenerationStatus"] or not _inSuno(obj):
				return
			status = _generationStatus(obj)
			if status == "progress" and not self._generationInProgress:
				self._generationInProgress = True
				ui.message(_("A sua música ainda está em processo de criação, por favor aguarde!"))
			elif status == "complete" and self._generationInProgress:
				self._generationInProgress = False
				ui.message(_("A sua música foi gerada com sucesso, pode descarregar no formato preferido!"))
		except Exception:
			log.debugWarning("Falha ao detetar o estado de geração do Suno", exc_info=True)

	def script_reportCurrentControl(self, gesture):
		"""Anuncia os dados do controlo atual para diagnóstico de acessibilidade."""
		obj = api.getFocusObject()
		self._createDiagnostic(obj)

	def _onCreateDiagnostic(self, evt):
		self._createDiagnostic(self._lastSunoObject)

	def _onOpenManual(self, evt):
		path = _manualPath()
		if not path:
			gui.messageBox(
				_("Não foi possível encontrar o manual do extra."),
				_("Acessibilidade para Suno AI"),
				wx.OK | wx.ICON_ERROR,
			)
			return
		try:
			os.startfile(path)
		except Exception:
			log.error("Falha ao abrir o manual do Suno", exc_info=True)
			gui.messageBox(
				_("Não foi possível abrir o manual do extra."),
				_("Acessibilidade para Suno AI"),
				wx.OK | wx.ICON_ERROR,
			)

	def _createDiagnostic(self, obj):
		if not _inSuno(obj):
			gui.messageBox(
				_("Não foi encontrado nenhum controlo sem etiqueta no Suno. Feche esta janela, volte ao Suno, coloque o foco no botão sem nome e tente novamente."),
				_("Diagnóstico do Suno AI"),
				wx.OK | wx.ICON_WARNING,
			)
			return
		parts = _diagnosticParts(obj)
		try:
			path = _saveDiagnostic(obj, parts)
		except Exception:
			log.error("Falha ao guardar o diagnóstico do Suno", exc_info=True)
			gui.messageBox(
				_("Não foi possível guardar o diagnóstico."),
				_("Diagnóstico do Suno AI"),
				wx.OK | wx.ICON_ERROR,
			)
			return
		if config.conf["sunoAccessibility"]["showManualConfirmation"]:
			gui.messageBox(
				_("Diagnóstico guardado com sucesso em:\n{path}").format(path=path),
				_("Diagnóstico do Suno AI"),
				wx.OK | wx.ICON_INFORMATION,
			)
		else:
			ui.message(_("Diagnóstico do Suno guardado"))
