"""Desktop confirmation UI, separate from native action execution."""
import gi
gi.require_version('Gtk','4.0')
from gi.repository import Gtk
from power_actions import ACTIONS

def create_dialog(app,action,execute):
 title,detail,label=ACTIONS[action]
 dialog=Gtk.MessageDialog(application=app,text=title,secondary_text=detail,modal=True)
 dialog.add_button('Cancel',Gtk.ResponseType.CANCEL)
 dialog.add_button(label,Gtk.ResponseType.ACCEPT)
 dialog.set_default_response(Gtk.ResponseType.CANCEL)
 def respond(dialog,response):
  if response!=Gtk.ResponseType.ACCEPT:dialog.destroy();app.quit();return
  try:execute()
  except Exception as error:
   dialog.set_property('text','Action failed')
   dialog.set_property('secondary-text',str(error))
   dialog.get_widget_for_response(Gtk.ResponseType.ACCEPT).set_sensitive(False)
   return
  dialog.destroy();app.quit()
 dialog.connect('response',respond)
 return dialog
