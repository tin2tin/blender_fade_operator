# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

import bpy
from bpy.types import Operator

from bpy.props import IntProperty


class SequencerCrossfadeSounds(Operator):
    """Do cross-fading volume animation of two selected sound strips"""

    bl_idname = "sequencer.crossfade_sounds"
    bl_label = "Crossfade sounds"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.scene and context.scene.sequence_editor and context.scene.sequence_editor.active_strip:
            return context.scene.sequence_editor.active_strip.type == 'SOUND'
        else:
            return False

    def execute(self, context):
        seq1 = None
        seq2 = None
        for s in context.scene.sequence_editor.sequences:
            if s.select and s.type == 'SOUND':
                if seq1 is None:
                    seq1 = s
                elif seq2 is None:
                    seq2 = s
                else:
                    seq2 = None
                    break
        if seq2 is None:
            self.report({'ERROR'}, "Select 2 sound strips")
            return {'CANCELLED'}
        if seq1.frame_final_start > seq2.frame_final_start:
            s = seq1
            seq1 = seq2
            seq2 = s
        if seq1.frame_final_end > seq2.frame_final_start:
            tempcfra = context.scene.frame_current
            context.scene.frame_current = seq2.frame_final_start
            seq1.keyframe_insert("volume")
            context.scene.frame_current = seq1.frame_final_end
            seq1.volume = 0
            seq1.keyframe_insert("volume")
            seq2.keyframe_insert("volume")
            context.scene.frame_current = seq2.frame_final_start
            seq2.volume = 0
            seq2.keyframe_insert("volume")
            context.scene.frame_current = tempcfra
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "The selected strips don't overlap")
            return {'CANCELLED'}


class SequencerCutMulticam(Operator):
    """Cut multi-cam strip and select camera"""

    bl_idname = "sequencer.cut_multicam"
    bl_label = "Cut multicam"
    bl_options = {'REGISTER', 'UNDO'}

    camera: IntProperty(
        name="Camera",
        min=1, max=32,
        soft_min=1, soft_max=32,
        default=1,
    )

    @classmethod
    def poll(cls, context):
        if context.scene and context.scene.sequence_editor and context.scene.sequence_editor.active_strip:
            return context.scene.sequence_editor.active_strip.type == 'MULTICAM'
        else:
            return False

    def execute(self, context):
        camera = self.camera

        s = context.scene.sequence_editor.active_strip

        if s.multicam_source == camera or camera >= s.channel:
            return {'FINISHED'}

        if not s.select:
            s.select = True

        cfra = context.scene.frame_current
        bpy.ops.sequencer.cut(frame=cfra, type='SOFT', side='RIGHT')
        for s in context.scene.sequence_editor.sequences_all:
            if s.select and s.type == 'MULTICAM' and s.frame_final_start <= cfra and cfra < s.frame_final_end:
                context.scene.sequence_editor.active_strip = s

        context.scene.sequence_editor.active_strip.multicam_source = camera
        return {'FINISHED'}


class SequencerDeinterlaceSelectedMovies(Operator):
    """Deinterlace all selected movie sources"""

    bl_idname = "sequencer.deinterlace_selected_movies"
    bl_label = "Deinterlace Movies"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.scene and context.scene.sequence_editor)

    def execute(self, context):
        for s in context.scene.sequence_editor.sequences_all:
            if s.select and s.type == 'MOVIE':
                s.use_deinterlace = True

        return {'FINISHED'}


def SetStripLevel(self, context, value):
    strip = context.scene.sequence_editor.active_strip
    if strip.type == 'SOUND':
        strip.volume = value
    else:
        strip.blend_alpha = value


def ExecuteFadeInOut(self, context, mode, duration, level):
    seq = context.scene.sequence_editor
    scn = context.scene
    strip = seq.active_strip
    tmp_current_frame = context.scene.frame_current
    self.mode = mode
    self.fade_duration = duration
    self.fade_level = level
    tmp_mode = (self.mode)

    if tmp_current_frame > strip.frame_final_start and tmp_current_frame < strip.frame_final_end:
        if (self.mode) == "INPLAYHEAD":
            self.fade_duration = tmp_current_frame-strip.frame_final_start
            tmp_mode = (self.mode)
            self.mode = 'IN'
        elif (self.mode) == "OUTPLAYHEAD":
            self.fade_duration = strip.frame_final_end - tmp_current_frame
            tmp_mode = (self.mode)
            self.mode = 'OUT'

    if strip.type == 'SOUND':
        fade_type = 'volume'
    else:
        fade_type = 'blend_alpha'

    if(self.mode) == 'OUT':
        scn.frame_current = strip.frame_final_end - self.fade_duration
        SetStripLevel(self, context, self.fade_level)
        strip.keyframe_insert(fade_type)

        scn.frame_current = strip.frame_final_end
        SetStripLevel(self, context, 0)
        strip.keyframe_insert(fade_type)

    elif(self.mode) == 'INOUT':
        strip_dur = strip.frame_final_end - strip.frame_final_start
        if (self.fade_duration*2) > (strip_dur):
            self.fade_duration = int(strip_dur/2)

        scn.frame_current = strip.frame_final_start
        SetStripLevel(self, context, 0)
        strip.keyframe_insert(fade_type)

        scn.frame_current += self.fade_duration
        SetStripLevel(self, context, self.fade_level)
        strip.keyframe_insert(fade_type)

        scn.frame_current = strip.frame_final_end - self.fade_duration
        SetStripLevel(self, context, self.fade_level)
        strip.keyframe_insert(fade_type)

        scn.frame_current = strip.frame_final_end
        SetStripLevel(self, context, 0)
        strip.keyframe_insert(fade_type)
    else:
        scn.frame_current = strip.frame_final_start
        SetStripLevel(self, context, 0)
        strip.keyframe_insert(fade_type)

        scn.frame_current += self.fade_duration
        SetStripLevel(self, context, self.fade_level)
        strip.keyframe_insert(fade_type)

    self.mode = tmp_mode
    context.scene.frame_current = tmp_current_frame


class SEQUENCER_OT_fade_in_out(bpy.types.Operator):
    """Add fades to active strip"""
    bl_label = "Fade Settings"
    bl_idname = "sequencer.fade_in_out"

    fade_mode: bpy.props.EnumProperty(
        name="Fade",
        description="Which fade to add",
        items=(
            ("IN", "In", "Add fade in"),
            ("OUT", "Out", "Add fade out"),
            ("INOUT", "In and Out", "Add fade in and out"),
            ("INPLAYHEAD", "To Playhead", "Add fade in to playhead"),
            ("OUTPLAYHEAD", "From Playhead", "Add fade out from playhead"),
        ),
        default="IN",
    )
    fade_duration: bpy.props.IntProperty(
        name="Duration",
        description="Number of frames to fade",
        min=1,
        max=250,
        default=25,
    )
    fade_level: bpy.props.FloatProperty(
        name="Maximum Level",
        description="Maximum level of fade",
        min=0.0,
        max=1.0,
        default=1.0,
    )

    def invoke(self, context, event):
        scene = context.scene
        if scene.animation_data is None:
            scene.animation_data_create()
        if scene.animation_data.action is None:
            action = bpy.data.actions.new(scene.name + "Action")
            scene.animation_data.action = action
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=220)

    def execute(self, context):
        ExecuteFadeInOut(self, context, self.fade_mode, self.fade_duration, self.fade_level)
        return {'FINISHED'}


classes = (
    SequencerCrossfadeSounds,
    SequencerCutMulticam,
    SequencerDeinterlaceSelectedMovies,
    SEQUENCER_OT_fade_in_out,
)
