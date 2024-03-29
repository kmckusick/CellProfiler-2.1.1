'''<b>Display Data On Image</b> 
produces an image with measured data on top of identified objects.
<hr>
This module displays either a single image measurement on an image of
your choosing, or one object measurement per object on top
of every object in an image. The display itself is an image which you
can save to a file using <b>SaveImages</b>.
'''

# CellProfiler is distributed under the GNU General Public License.
# See the accompanying file LICENSE for details.
# 
# Copyright (c) 2003-2009 Massachusetts Institute of Technology
# Copyright (c) 2009-2014 Broad Institute
# 
# Please see the AUTHORS file for credits.
# 
# Website: http://www.cellprofiler.org


import numpy as np

import cellprofiler.cpmodule as cpm
import cellprofiler.settings as cps
import cellprofiler.cpimage as cpi
import cellprofiler.objects as cpo
import cellprofiler.workspace as cpw
import cellprofiler.measurements as cpmeas
import cellprofiler.preferences as cpprefs
from cellprofiler.modules.identify import M_LOCATION_CENTER_X, M_LOCATION_CENTER_Y

OI_OBJECTS = "Object"
OI_IMAGE = "Image"

E_FIGURE = "Figure"
E_AXES = "Axes"
E_IMAGE = "Image"

CT_COLOR = "Color"
CT_TEXT = "Text"

class DisplayDataOnImage(cpm.CPModule):
    module_name = 'DisplayDataOnImage'
    category = 'Data Tools'
    variable_revision_number = 5
    
    def create_settings(self):
        """Create your settings by subclassing this function
        
        create_settings is called at the end of initialization.
        
        You should create the setting variables for your module here:
            # Ask the user for the input image
            self.image_name = cellprofiler.settings.ImageNameSubscriber(...)
            # Ask the user for the name of the output image
            self.output_image = cellprofiler.settings.ImageNameProvider(...)
            # Ask the user for a parameter
            self.smoothing_size = cellprofiler.settings.Float(...)
        """
        self.objects_or_image = cps.Choice(
            "Display object or image measurements?",
            [OI_OBJECTS, OI_IMAGE],doc = """
            <ul>
            <li><i>%(OI_OBJECTS)s</i> displays measurements made on
            objects.</li>
            <li><i>%(OI_IMAGE)s</i> displays a single measurement made
            on an image.</li> 
            </ul>"""%globals())
        
        self.objects_name = cps.ObjectNameSubscriber(
            "Select the input objects", cps.NONE, doc = """
            <i>(Used only when displaying object measurements)</i><br>
            Choose the name of objects identified by some previous
            module (such as <b>IdentifyPrimaryObjects</b> or
            <b>IdentifySecondaryObjects</b>).""")
        
        def object_fn():
            if self.objects_or_image == OI_OBJECTS:
                return self.objects_name.value
            else:
                return cpmeas.IMAGE
        self.measurement = cps.Measurement(
            "Measurement to display", object_fn,doc="""
            Choose the measurement to display. This will be a measurement
            made by some previous module on either the whole image (if
            displaying a single image measurement) or on the objects you
            selected.""")
        
        self.wants_image = cps.Binary(
            "Display background image?", True,
            doc="""Choose whether or not to display the measurements on
            a background image. Usually, you will want to see the image
            context for the measurements, but it may be useful to save
            just the overlay of the text measurements and composite the
            overlay image and the original image later. Choose "Yes" to
            display the measurements on top of a background image or "No"
            to display the measurements on a black background.""")
        self.image_name = cps.ImageNameSubscriber(
            "Select the image on which to display the measurements", cps.NONE, doc="""
            Choose the image to be displayed behind the measurements.
            This can be any image created or loaded by a previous module.
            If you have chosen not to display the background image, the image
            will only be used to determine the dimensions of the displayed image""")
        
        self.color_or_text = cps.Choice(
            "Display mode", [CT_TEXT, CT_COLOR],
            doc = """<i>(Used only when displaying object measurements)</i><br>
            Choose how to display the measurement information. If you choose
            %(CT_TEXT)s, <b>DisplayDataOnImage</b> will display the numeric
            value on top of each object. If you choose %(CT_COLOR)s,
            <b>DisplayDataOnImage</b> will convert the image to grayscale, if
            necessary, and display the portion of the image within each object
            using a hue that indicates the measurement value relative to
            the other objects in the set using the default color map.
            """ % globals()
            )
        
        self.colormap = cps.Colormap(
            "Color map",
            doc = """<i>(Used only when displaying object measurements)</i><br>
            This is the color map used as the color gradient for coloring the
            objects by their measurement values.
            """)        
        self.text_color = cps.Color(
            "Text color","red",doc="""
            This is the color that will be used when displaying the text.
            """)
        
        self.display_image = cps.ImageNameProvider(
            "Name the output image that has the measurements displayed","DisplayImage",doc="""
            The name that will be given to the image with
            the measurements superimposed. You can use this name to refer to the image in
            subsequent modules (such as <b>SaveImages</b>).""")
        
        self.font_size = cps.Integer(
            "Font size (points)", 10, minval=1)
        
        self.decimals = cps.Integer(
            "Number of decimals", 2, minval=0)
        
        self.saved_image_contents = cps.Choice(
            "Image elements to save",
            [E_IMAGE, E_FIGURE, E_AXES],doc="""
            This setting controls the level of annotation on the image:
            <ul>
            <li><i>%(E_IMAGE)s:</i> Saves the image with the overlaid measurement annotations.</li>
            <li><i>%(E_AXES)s:</i> Adds axes with tick marks and image coordinates.</li>
            <li><i>%(E_FIGURE)s:</i> Adds a title and other decorations.</li></ul>"""%globals())
        
        self.offset = cps.Integer(
            "Annotation offset (in pixels)",0,doc="""
            Add a pixel offset to the measurement. Normally, the text is
            placed at the object (or image) center, which can obscure relevant features of
            the object. This setting adds a specified offset to the text, in a random
            direction.""")
        
    def settings(self):
        """Return the settings to be loaded or saved to/from the pipeline
        
        These are the settings (from cellprofiler.settings) that are
        either read from the strings in the pipeline or written out
        to the pipeline. The settings should appear in a consistent
        order so they can be matched to the strings in the pipeline.
        """
        return [self.objects_or_image, self.objects_name, self.measurement,
                self.image_name, self.text_color, self.display_image,
                self.font_size, self.decimals, self.saved_image_contents,
                self.offset, self.color_or_text, self.colormap, 
                self.wants_image]
    
    def visible_settings(self):
        """The settings that are visible in the UI
        """
        result = [self.objects_or_image]
        if self.objects_or_image == OI_OBJECTS:
            result += [self.objects_name]
        result += [self.measurement, self.wants_image, self.image_name]
        if self.objects_or_image == OI_OBJECTS:
            result += [self.color_or_text]
        if self.use_color_map():
            result += [self.colormap]
        else:
            result += [ self.text_color, self.font_size, self.decimals,
                        self.offset]
        result += [self.display_image, self.saved_image_contents]
        return result
        
    def use_color_map(self):
        '''True if the measurement values are rendered using a color map'''
        return self.objects_or_image == OI_OBJECTS and \
               self.color_or_text == CT_COLOR
    
    def run(self, workspace):
        import matplotlib
        import matplotlib.cm
        import matplotlib.backends.backend_agg
        import matplotlib.transforms
        from cellprofiler.gui.cpfigure_tools import figure_to_image, only_display_image
        #
        # Get the image
        #
        image = workspace.image_set.get_image(self.image_name.value)
        if self.wants_image:
            pixel_data = image.pixel_data
        else:
            pixel_data = np.zeros(image.pixel_data.shape[:2])
        if self.objects_or_image == OI_OBJECTS:
            objects = workspace.object_set.get_objects(self.objects_name.value)
        workspace.display_data.pixel_data = pixel_data
        if self.use_color_map():
            workspace.display_data.labels = objects.segmented
        #
        # Get the measurements and positions
        #
        measurements = workspace.measurements
        if self.objects_or_image == OI_IMAGE:
            value = measurements.get_current_image_measurement(
                self.measurement.value)
            values = [value]
            x = [pixel_data.shape[1] / 2]
            x_offset = np.random.uniform(high=1.0,low=-1.0)
            x[0] += x_offset
            y = [pixel_data.shape[0] / 2]
            y_offset = np.sqrt(1 - x_offset**2)
            y[0] += y_offset
        else:
            values = measurements.get_current_measurement(
                self.objects_name.value,
                self.measurement.value)
            if len(values) < objects.count:
                temp = np.zeros(objects.count, values.dtype)
                temp[:len(values)] = values
                temp[len(values):] = np.nan
                values = temp
            x = measurements.get_current_measurement(
                self.objects_name.value, M_LOCATION_CENTER_X)
            x_offset = np.random.uniform(high=1.0,low=-1.0,size=x.shape)
            y_offset = np.sqrt(1 - x_offset**2)
            x += self.offset.value*x_offset
            y = measurements.get_current_measurement(
                self.objects_name.value, M_LOCATION_CENTER_Y)
            y += self.offset.value*y_offset
            mask = ~(np.isnan(values) | np.isnan(x) | np.isnan(y))
            values = values[mask]
            x = x[mask]
            y = y[mask]
            workspace.display_data.mask = mask
        workspace.display_data.values = values
        workspace.display_data.x = x
        workspace.display_data.y = y
        fig = matplotlib.figure.Figure()
        axes = fig.add_subplot(1,1,1)
        def imshow_fn(pixel_data):
            # Note: requires typecast to avoid failure during
            #       figure_to_image (IMG-764)
            img = pixel_data * 255
            img[img < 0] = 0
            img[img > 255] = 255
            img = img.astype(np.uint8)
            axes.imshow(img, cmap = matplotlib.cm.Greys_r)
        self.display_on_figure(workspace, axes, imshow_fn)

        canvas = matplotlib.backends.backend_agg.FigureCanvasAgg(fig)
        if self.saved_image_contents == E_AXES:
            fig.set_frameon(False)
            if not self.use_color_map():
                fig.subplots_adjust(0.1,.1,.9,.9,0,0)
            shape = pixel_data.shape
            width = float(shape[1]) / fig.dpi
            height = float(shape[0]) / fig.dpi
            fig.set_figheight(height)
            fig.set_figwidth(width)
        elif self.saved_image_contents == E_IMAGE:
            if self.use_color_map():
                fig.axes[1].set_visible(False)
            only_display_image(fig, pixel_data.shape)
        else:
            if not self.use_color_map():
                fig.subplots_adjust(.1,.1,.9,.9,0,0)
            
        pixel_data = figure_to_image(fig, dpi=fig.dpi)
        image = cpi.Image(pixel_data)
        workspace.image_set.add(self.display_image.value, image)
        
    def run_as_data_tool(self, workspace):
        # Note: workspace.measurements.image_set_number contains the image
        #    number that should be displayed.
        import wx
        import loadimages as LI
        import os.path
        im_id = self.image_name.value
        
        m = workspace.measurements
        image_name = self.image_name.value
        pathname_feature = "_".join((LI.C_PATH_NAME, image_name))
        filename_feature = "_".join((LI.C_FILE_NAME, image_name))
        if not all([m.has_feature(cpmeas.IMAGE, f)
                    for f in pathname_feature, filename_feature]):
            with wx.FileDialog(
                None, 
                message = "Image file for display",
                wildcard = "Image files (*.tif, *.png, *.jpg)|*.tif;*.png;*.jpg|"
                "All files (*.*)|*.*") as dlg:
                if dlg.ShowModal() != wx.ID_OK:
                    return
            pathname, filename = os.path.split(dlg.Path)
        else:
            pathname = m.get_current_image_measurement(pathname_feature)
            filename = m.get_current_image_measurement(filename_feature)
        
        # Add the image to the workspace ImageSetList
        image_set_list = workspace.image_set_list
        image_set = image_set_list.get_image_set(0)
        ip = LI.LoadImagesImageProvider(im_id, pathname, filename)
        image_set.providers.append(ip)
        
        self.run(workspace)
        
    def display(self, workspace, figure):
        figure.set_subplots((1, 1))
        ax = figure.subplot(0, 0)
        title = "%s_%s" % (self.objects_name.value, self.measurement.value)
        def imshow_fn(pixel_data):
            if pixel_data.ndim == 3:
                figure.subplot_imshow_color(0, 0, pixel_data, title=title)
            else:
                figure.subplot_imshow_grayscale(0, 0, pixel_data, title=title)

        self.display_on_figure(workspace, ax, imshow_fn)
        
    def display_on_figure(self, workspace, axes, imshow_fn):
        import matplotlib
        import matplotlib.cm
        
        if self.use_color_map():
            labels = workspace.display_data.labels
            pixel_data = workspace.display_data.pixel_data
            if pixel_data.ndim == 3:
                pixel_data = np.sum(pixel_data, 2) / pixel_data.shape[2]
            colormap_name = self.colormap.value
            if colormap_name == cps.DEFAULT:
                colormap_name = cpprefs.get_default_colormap()
            colormap = matplotlib.cm.get_cmap(colormap_name)
            values = workspace.display_data.values
            vmask = workspace.display_data.mask
            colors = np.ones((len(vmask) + 1, 4))
            colors[1:][~vmask, :3] = 1
            sm = matplotlib.cm.ScalarMappable(cmap = colormap)
            sm.set_array(values)
            colors[1:][vmask, :] = sm.to_rgba(values)
            img = colors[labels, :3] * pixel_data[:, :, np.newaxis]
            imshow_fn(img)
            assert isinstance(axes, matplotlib.axes.Axes)
            figure = axes.get_figure()
            assert isinstance(figure, matplotlib.figure.Figure)
            figure.colorbar(sm, ax=axes)
        else:
            imshow_fn(workspace.display_data.pixel_data)
            for x, y, value in zip(workspace.display_data.x,
                                   workspace.display_data.y,
                                   workspace.display_data.values):
                try:
                    fvalue = float(value)
                    svalue = "%.*f"%(self.decimals.value, value)
                except:
                    svalue = str(value)
                
                text = matplotlib.text.Text(x=x, y=y, text=svalue,
                                            size=self.font_size.value,
                                            color=self.text_color.value,
                                            verticalalignment='center',
                                            horizontalalignment='center')
                axes.add_artist(text)
            
    def upgrade_settings(self, setting_values, variable_revision_number, 
                         module_name, from_matlab):
        if from_matlab and (variable_revision_number == 2):
            object_name, category, feature_nbr, image_name, size_scale, \
                display_image, data_image, dpi_to_save, \
                saved_image_contents = setting_values
            objects_or_image = (OI_IMAGE if object_name == cpmeas.IMAGE
                                else OI_OBJECTS)
            measurement = '_'.join((category, feature_nbr, image_name, size_scale))
            setting_values = [
                objects_or_image, object_name, measurement, display_image,
                "red", data_image, dpi_to_save, saved_image_contents]
            from_matlab = False
            variable_revision_number = 1
        if variable_revision_number == 1:
            objects_or_image, objects_name, measurement, \
                image_name, text_color, display_image, \
                dpi, saved_image_contents = setting_values
            setting_values = [objects_or_image, objects_name, measurement,
                              image_name, text_color, display_image,
                              10, 2, saved_image_contents]
            variable_revision_number = 2

        if variable_revision_number == 2:
            '''Added annotation offset'''
            setting_values = setting_values + ["0"]
            variable_revision_number = 3
            
        if variable_revision_number == 3:
            # Added color map mode
            setting_values = setting_values + [ 
                CT_TEXT, cpprefs.get_default_colormap() ]
            variable_revision_number = 4
            
        if variable_revision_number == 4:
            # added wants_image
            setting_values = setting_values + [ cps.YES ]
            variable_revision_number = 5
        
        return setting_values, variable_revision_number, from_matlab
        

    
if __name__ == "__main__":
    ''' For debugging purposes only...
    '''
    import wx
    from cellprofiler.gui.datatoolframe import DataToolFrame
    app = wx.PySimpleApp()

    tool_name = 'DisplayDataOnImage'
    dlg = wx.FileDialog(None, "Choose data output file for %s data tool" %
                        tool_name, wildcard="*.mat",
                        style=(wx.FD_OPEN | wx.FILE_MUST_EXIST))
    if dlg.ShowModal() == wx.ID_OK:
        data_tool_frame = DataToolFrame(None, module_name=tool_name, measurements_file_name = dlg.Path)
    data_tool_frame.Show()
    
    app.MainLoop()
