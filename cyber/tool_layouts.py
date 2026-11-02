# SPDX-License-Identifier: AGPL-3.0-only
"""Original presentation metadata for existing tools. No processing algorithms."""

ACTIONS={
 'Print':'Print…','Scan':'Build PDF','PDF Editor':'Apply PDF changes',
 'PVC Tool':'Create card sheet','Auto ID Card':'Arrange ID cards','Photo Print':'Create photo sheet',
 'Photo & Sign':'Resize image','PAN Tool':'Prepare attachments','Merge Tool':'Merge documents',
 'Compress':'Compress file','Convert':'Convert document','Mini Print':'Create mini-print sheet',
 'QR Generator':'Create QR code','Resume Maker':'Build resume','Bill Maker':'Build invoice',
 'Signature Check':'Inspect signatures','Portal PDF Pack':'Create portal PDF',
 'Auto Crop':'Straighten pages','Edit Screenshot':'Apply image changes','Screen Recording':'Start recording'}

# Order is visual only. All original option keys, defaults and handlers survive.
FIELD_GROUPS={
 'Print':[('PAGES & COPIES',('pages','copies')),('OUTPUT',('colour','duplex','rotation'))],
 'Scan':[('SCAN QUALITY',('dpi',))],
 'PDF Editor':[('OPERATION',('mode','page')),('TEXT',('find','text','size')),('REGION & OCR',('box','language'))],
 'PVC Tool':[('CARD SIZE',('width','height')),('SHEET & ALIGNMENT',('paper','autocrop'))],
 'Auto ID Card':[('CARD SIZE',('width','height')),('FRONT / BACK SHEET',('paper','autocrop'))],
 'Photo Print':[('PHOTO SIZE',('width','height','copies')),('SHEET & CROP',('paper','background','box'))],
 'Photo & Sign':[('OUTPUT SIZE',('width','height','kb','format')),('ADJUSTMENTS',('rotation','brightness','contrast')),('BACKGROUND & CROP',('background','box'))],
 'PAN Tool':[('ATTACHMENT APPEARANCE',('background','box'))],
 'Compress':[('OUTPUT TARGET',('type','kb'))],
 'Convert':[('OUTPUT FORMAT',('format','dpi'))],
 'Mini Print':[('SHEET LAYOUT',('layout','paper'))],
 'QR Generator':[('CONTENT',('text',)),('OUTPUT',('format','size','color'))],
 'Resume Maker':[('DOCUMENT',('design','format')),('IDENTITY',('name','role','phone','email','city')),('PROFILE',('summary','experience')),('QUALIFICATIONS',('education','skills','projects'))],
 'Bill Maker':[('DOCUMENT',('design','number')),('CUSTOMER',('customer','phone','notes'))],
 'Signature Check':[('LOCAL TRUST',('trust',))],
 'Portal PDF Pack':[('PORTAL LIMIT',('kb','bw'))],
 'Auto Crop':[('DOCUMENT APPEARANCE',('bw',))],
 'Edit Screenshot':[('SELECTION',('box',)),('REPLACEMENT',('text','size')),('APPEARANCE',('color','background','inpaint'))],
 'Screen Recording':[('CAPTURE',('fps','monitor')),('PRIVACY',('masks',))],
 'Merge Tool':[]}

PURPOSE={
 'Print':'Review pages, choose your printer, then print.',
 'Scan':'Capture pages, review their order, and export one PDF.',
 'Signature Check':'Inspect existing signatures and offline certificate trust.',
 'Portal PDF Pack':'Prepare local attachments within a portal size limit.'}

SEARCH_ALIASES={'Signature Check':'e sign signature validation certificate',
                'Portal PDF Pack':'jharsewa attachments portal'}
